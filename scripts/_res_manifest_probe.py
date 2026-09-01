#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_res_manifest_probe.py -- 原版资源清单探测（草稿）

扫全镜像 X:NAME.EXT 资源名 → 聚类成阵列 → 找加载点(push <addr> 到资源加载函数)。
"""
import os, re, struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "scripts/_unpacked_mem.bin")
BASE = 0x400000
MEM = open(BIN, "rb").read()

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def rd(va, n):
    off = va - BASE
    return MEM[off:off + n]


def cstr(va, maxlen=24):
    b = rd(va, maxlen)
    z = b.find(0)
    return b[:z if z >= 0 else maxlen]


# ---------- 1. 资源名扫描 ----------
PAT = re.compile(rb"[A-F]:[A-Z0-9_]{1,12}\.[A-Z0-9]{2,3}")

def scan_names():
    out = {}
    for m in PAT.finditer(MEM):
        if m.end() < len(MEM) and MEM[m.end()] == 0:
            va = BASE + m.start()
            out[va] = m.group().decode("ascii")
    return out


# ---------- 2. 全镜像指令索引（用于找 push 立即数 / call 目标） ----------
def build_insns():
    """反汇编全镜像（skipdata），返回 (addr, size, mnemonic, op_str, raw) 列表。"""
    insns = []
    off = 0
    n = len(MEM)
    while off < n:
        try:
            got = False
            for i in md.disasm(MEM[off:off + 16], BASE + off):
                insns.append((i.address, i.size, i.mnemonic, i.op_str, i.bytes))
                off += i.size
                got = True
                break
            if not got:
                off += 1
        except Exception:
            off += 1
    return insns


def immediate_operands(mnem, op_str):
    """提取立即数操作数（capstone 小立即数无 0x 前缀，需手动补）。"""
    vals = []
    for tok in op_str.split(","):
        tok = tok.strip()
        m = re.fullmatch(r"(0x[0-9a-f]+|[0-9]+)", tok)
        if m:
            s = m.group(1)
            vals.append(int(s, 16) if s.startswith("0x") else int(s))
    return vals


def main():
    names = scan_names()
    print("资源名总数:", len(names))

    insns = build_insns()
    print("指令数:", len(insns))

    # 3. 找所有 call 到资源加载助手的站点，并回溯最近的 push 立即数
    TARGETS = {0x4ec8c0: "selector_ctor", 0x4802e0: "res_loader", 0x492800: "res_forward3"}
    sites = []
    for k in range(len(insns)):
        addr, sz, mn, op, raw = insns[k]
        if mn != "call":
            continue
        vals = immediate_operands(mn, op)
        if not vals or vals[0] not in TARGETS:
            continue
        tgt = vals[0]
        # 回溯最多 8 条指令，收集 push 立即数
        pushes = []
        for j in range(k - 1, max(-1, k - 12), -1):
            a2, s2, m2, o2, r2 = insns[j]
            if m2 == "push":
                vv = immediate_operands(m2, o2)
                if vv:
                    pushes.append((a2, vv[0]))
            elif m2.startswith("call"):
                break
        sites.append((addr, tgt, TARGETS[tgt], pushes))

    print("\n=== 资源加载调用点 ===")
    hits = {}
    for addr, tgt, tag, pushes in sites:
        for pa, pv in pushes:
            if pv in names:
                hits.setdefault((addr, tgt, tag), []).append((pa, pv, names[pv]))
    for (addr, tgt, tag), hs in sorted(hits.items()):
        print("  0x%06x call 0x%x (%s): %s" % (
            addr, tgt, tag, ", ".join("push %s@0x%x" % (nm, pv) for pa, pv, nm in hs)))

    # 4. 对每个资源名地址做全镜像引用扫描（push / mov imm / 任意 4 字节字面）
    print("\n=== 资源名引用点（raw 4-byte 字面 + push 立即数）===")
    refs = {}
    for va, nm in names.items():
        pat = struct.pack("<I", va)
        hits2 = []
        off = 0
        while True:
            i = MEM.find(pat, off)
            if i < 0:
                break
            hits2.append(BASE + i)
            off = i + 1
        if hits2:
            refs[va] = hits2
    for va in sorted(refs):
        print("  %-20s @0x%06x -> %s" % (names[va], va,
              ", ".join("0x%x" % x for x in refs[va][:6]) + (" ..." if len(refs[va]) > 6 else "")))


if __name__ == "__main__":
    main()
