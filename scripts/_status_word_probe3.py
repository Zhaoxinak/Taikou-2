#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续170(B)：区分 word[+0x2c] bit15(0x8000) vs bit7(0x80) 两种「不在」语义。
按函数共现启发：某函数若既访问 word/byte ptr [..+0x2c]（或 +0x2d），又对该寄存器
高/低字节做 or/and/test 0x80/0x7f，则把 bit 操作归到状态字。输出每个函数对该字
SET/CLR(或and)/TEST 了 bit15 还是 bit7，用于归类语义。纯静态。"""
import os, re, bisect
from collections import defaultdict
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()

ANCHOR = {
    0x49a7d0: "set_lord_idx", 0x49a880: "inc_loyalty", 0x49ffc0: "affinity_score",
    0x49c460: "S15_set_a", 0x49c4b0: "S15_set_b", 0x49a990: "castle_rec_copy",
    0x47b900: "display_msg", 0x4ebd60: "RNG", 0x45e3e0: "build_cand_pool",
    0x49f5e0: "get_player", 0x49f830: "get_slot", 0x470690: "is_alive",
    0x47fc60: "sndata_fanout", 0x49b960: "shared_setter_lib", 0x441cc0: "武将選択",
    0x49a750: "copy_prov", 0x4a35e0: "s6_add", 0x49a7e0: "set_status_b8_10",
    0x49f6b0: "get_ctx", 0x4ebcd0: "sat_sub", 0x4ebca0: "sat_add",
    0x4a5571: "継承転封", 0x4a3920: "全員浪人化A", 0x46a4a0: "主君再割当",
    0x452b21: "登用", 0x4a5033: "出奔", 0x4a580e: "転属", 0x4a3eab: "役職解除",
    0x4c3322: "功勲结算", 0x4cb9e0: "相性離反", 0x440e19: "玩家改易",
    0x40ff2c: "浪人生成A", 0x41004b: "浪人生成B", 0x4dd7c0: "S5",
    0x49ba30: "S6b2_4", 0x49bd50: "set_status", 0x49bd70: "set_status", 0x49bd90: "set_status",
    0x4a3260: "inc_loyalty2", 0x4cf240: "全局复位", 0x4cf280: "单记录复位",
}

def dis(va, n):
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.skipdata = True
    off = va - BASE
    return list(md.disasm(bytes(MEM[off:off+n]), va))

def signed_disp(op):
    m = re.search(r'\[([^\]]+)\]', op)
    if not m: return None
    inside = m.group(1)
    adds = re.findall(r'([+\-])\s*(0x[0-9a-f]+|\d+)', inside)
    if not adds: return 0
    val = 0
    for s, h in adds:
        nv = int(h, 16) if h.startswith('0x') else int(h, 10)
        val += nv * (1 if s == '+' else -1)
    return val

def is_status_mem(op):
    """内存操作数是否解析到 +0x2c(状态字) 或 +0x2d(状态字高字节)。"""
    if "ptr [" not in op.lower(): return False
    d = signed_disp(op)
    if d == 0x2c: return "lo"      # word/byte 低字节 at +0x2c
    if d == 0x2d: return "hi"      # byte 高字节 at +0x2d
    return None

INS = dis(BASE, len(MEM))
all_funcs = set([0x4f44b0, 0x400000])
for i in INS:
    if i.mnemonic == "call" and i.op_str.startswith("0x"):
        try: all_funcs.add(int(i.op_str, 16))
        except: pass
all_funcs = sorted(all_funcs)
def func_of(va): return all_funcs[max(0, bisect.bisect_right(all_funcs, va) - 1)]
func_insns = defaultdict(list)
for i in INS: func_insns[func_of(i.address)].append(i)

results = {}  # fn -> {'bit15':set(kinds), 'bit7':set(kinds), 'touch':bool, 'detail':[]}
for fn, ilist in func_insns.items():
    touch = False
    status_base = None  # 'a'/'b'/... 表示该寄存器持有 word[+0x2c]
    loads = []  # 记录所有把 word[+0x2c] 载入的寄存器基字母
    for ins in ilist:
        m, op = ins.mnemonic, ins.op_str
        if is_status_mem(op): touch = True
        lm = re.match(r'(e?[a-z]{2}),\s*word ptr \[([^\]]+)\]', op)
        if lm and m == "mov":
            d = signed_disp(lm.group(2))
            if d == 0x2c:
                r = lm.group(1); loads.append(r.lstrip('e')[0] if r.lstrip('e') else r[0])
    if loads: status_base = loads[0]
    ops = []
    for ins in ilist:
        m, op = ins.mnemonic, ins.op_str
        # 字节寄存器 bit 操作（ah=bit15 高字节, al=bit7 低字节）
        rm = re.match(r'(ah|al),\s*(0x[0-9a-f]+|\d+)$', op)
        if rm and m in ("or", "and", "test"):
            imm = int(rm.group(2), 16) if rm.group(2).startswith('0x') else int(rm.group(2), 10)
            if imm in (0x80, 0x7f) and (status_base and rm.group(1)[0] == status_base or touch):
                ops.append((ins.address, "ah" if rm.group(1) == "ah" else "al", m, imm))
        # 16 位寄存器 bit 操作
        rm2 = re.match(r'(e?[a-z]{2}),\s*(0x[0-9a-f]+|\d+)$', op)
        if rm2 and m in ("or", "and", "test"):
            r = rm2.group(1); imm = int(rm2.group(2), 16) if rm2.group(2).startswith('0x') else int(rm2.group(2), 10)
            if imm in (0x8000, 0x7fff, 0x80, 0x7f) and (status_base and r.lstrip('e')[0] == status_base or touch):
                ops.append((ins.address, "ax", m, imm))
        # 内存立即数形式
        mm = re.match(r'(?:word|byte) ptr \[([^\]]+)\],\s*(0x[0-9a-f]+|\d+)$', op)
        if mm and m in ("or", "and", "test"):
            d = signed_disp(mm.group(1)); imm = int(mm.group(2), 16) if mm.group(2).startswith('0x') else int(mm.group(2), 10)
            if d == 0x2c and imm in (0x8000, 0x7fff, 0x80, 0x7f):
                ops.append((ins.address, "mem_lo", m, imm))
            if d == 0x2d and imm in (0x80, 0x7f):
                ops.append((ins.address, "mem_hi", m, imm))
    if not touch:
        continue  # 共现启发：只保留既碰 +0x2c 又做 bit 操作的函数
    d15, d7 = set(), set()
    detail = []
    for (a, kind, m, imm) in ops:
        if kind == "ah": bit = "bit15"
        elif kind == "al": bit = "bit7"
        elif kind == "ax":
            bit = "bit15" if imm in (0x8000, 0x7fff) else "bit7"
        elif kind == "mem_lo":
            bit = "bit15" if imm in (0x8000, 0x7fff) else "bit7"
        elif kind == "mem_hi":
            bit = "bit15"
        else: continue
        k = "SET" if m == "or" else ("CLR" if m == "and" else "TEST")
        if bit == "bit15": d15.add(k)
        else: d7.add(k)
        detail.append((a, bit, k, m, imm, kind))
    if d15 or d7:
        results[fn] = (d15, d7, detail)

print("共现命中函数数: %d\n" % len(results))
# 分类：SET bit15 的 / SET bit7 的
for label, want in (("=== SET/CLEAR bit15 的函数 ===", "bit15"),
                    ("=== SET/CLEAR bit7 的函数 ===", "bit7")):
    print(label)
    for fn in sorted(results):
        d15, d7, detail = results[fn]
        target = d15 if want == "bit15" else d7
        if not target: continue
        anchors = set()
        for j in dis(fn, 0x300):
            if j.mnemonic == "call" and j.op_str.startswith("0x"):
                try:
                    t = int(j.op_str, 16)
                    if t in ANCHOR: anchors.add(ANCHOR[t])
                except: pass
        # 只看该 bit 的操作
        dl = [x for x in detail if (x[1] == want)]
        print("0x%06x  [%s]  %s" % (fn, " ".join(sorted(target)), " ".join(sorted(anchors))))
        for (a, bit, k, m, imm, kind) in dl:
            print("    0x%x  %-5s %s %s" % (a, "%s:%s" % (bit, k), m, ("0x%x" % imm) if imm >= 0x100 else str(imm)))
    print()
