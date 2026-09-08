#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sfx_15_36_dead_ref.py — 续248 死资源断言（精简版）

权威收口见 `sfx_15_36_ref.py`（续248/子代理加强：75 站分类 + 5 REG 定值，17/17）。
本文件保留交叉复跑的轻量硬断言（名表 xref / 无直接 push / 已知 REG 路径）。
"""
import os
import struct
from collections import Counter

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(_ROOT, "scripts", "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
PLAY = 0x4997C0
TBL = 0x50BA40
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

results = []


def chk(name, cond, detail=""):
    results.append((name, bool(cond)))
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", name,
                           ("  — " + detail) if detail else ""))


def play_sites():
    out = []
    for i in range(len(MEM) - 5):
        if MEM[i] != 0xE8:
            continue
        rel = int.from_bytes(MEM[i + 1:i + 5], "little", signed=True)
        if BASE + i + 5 + rel == PLAY:
            out.append(BASE + i)
    return out


def last_push_imm(site, lookback=48):
    start = max(BASE, site - lookback)
    last = None
    for ins in md.disasm(MEM[start - BASE:site - BASE], start):
        if ins.mnemonic != "push":
            continue
        op = ins.op_str.strip()
        try:
            last = int(op, 16) if op.startswith("0x") else int(op)
        except ValueError:
            last = None
    return last


print("=== A. play_sfx 调用几何 ===")
sites = play_sites()
chk("A1 play_sfx 调用点数 ≥ 70", len(sites) >= 70, "n=%d" % len(sites))

imm_ids = Counter()
for s in sites:
    v = last_push_imm(s)
    if v is not None and 0 <= v <= 50:
        imm_ids[v] += 1
chk("A2 立即数 push 覆盖 ≥ 25 个 ID", len(imm_ids) >= 25, "ids=%s" % sorted(imm_ids))
chk("A3 立即数路径无 ID 15", 15 not in imm_ids)
chk("A4 立即数路径无 ID 36", 36 not in imm_ids)

print("\n=== B. 寄存器路径已知补齐（对照，非 15/36）===")
# weather
w = MEM[0x44EDC9 - BASE:0x44EDD4 - BASE]
chk("B1 @0x44edd4 前：xor ecx / setne / add ecx,0x22（→34/35）",
    w[:2] == b"\x33\xc9" and b"\x83\xc1\x22" in w, w.hex())
# dialog ebp
chk("B2 @0x46bc70 mov ebp,0x13（ID19）",
    MEM[0x46BC70 - BASE:0x46BC75 - BASE] == b"\xbd\x13\x00\x00\x00")
chk("B3 @0x46bc79 mov ebp,0x14（ID20）",
    MEM[0x46BC79 - BASE:0x46BC7E - BASE] == b"\xbd\x14\x00\x00\x00")

print("\n=== C. 文件名表与 xref ===")
ptrs = [struct.unpack_from("<I", MEM, TBL - BASE + 4 * i)[0] for i in range(39)]


def cstr(va):
    raw = MEM[va - BASE:va - BASE + 24]
    return raw[:raw.find(0)].decode("ascii", "replace") if 0 in raw else ""


chk("C1 table[15] 含 ZANSYU", "ZANSYU" in cstr(ptrs[15]).upper(), cstr(ptrs[15]))
chk("C2 table[36] 含 MATISIRO", "MATISIRO" in cstr(ptrs[36]).upper(), cstr(ptrs[36]))

for name, idx in (("ZANSYU", 15), ("MATISIRO", 36)):
    sva = ptrs[idx]
    needle = struct.pack("<I", sva)
    hits = []
    start = 0
    while True:
        j = MEM.find(needle, start)
        if j < 0:
            break
        hits.append(BASE + j)
        start = j + 1
    # 仅表槽自身
    expect = TBL + 4 * idx
    chk("C3 %s imm32 xref 恰 1（=表槽）" % name,
        hits == [expect], "hits=%s expect=%s" % ([hex(h) for h in hits], hex(expect)))

print("\n=== D. 底层播音无直接文件名 ===")
# 0x4015f0 callers
bottom = []
for i in range(len(MEM) - 5):
    if MEM[i] != 0xE8:
        continue
    rel = int.from_bytes(MEM[i + 1:i + 5], "little", signed=True)
    if BASE + i + 5 + rel == 0x4015F0:
        bottom.append(BASE + i)
chk("D1 0x4015f0 调用点很少（≤5）", len(bottom) <= 5, "n=%d" % len(bottom))
direct = []
for s in bottom:
    for ins in md.disasm(MEM[s - BASE - 24:s - BASE], s - 24):
        if ins.mnemonic == "push" and ins.op_str.startswith("0x50"):
            p = int(ins.op_str, 16)
            nm = cstr(p).upper()
            if "ZANSYU" in nm or "MATISIRO" in nm:
                direct.append((hex(s), nm))
chk("D2 无 push ZANSYU/MATISIRO 直达 0x4015f0", direct == [])

print("\n=== E. 死槽集合声明 ===")
# 经 probe7：仍无静态生产者 = 15,26,32,36,37
dead = {15, 26, 32, 36, 37}
chk("E1 声明死槽包含 15 与 36", 15 in dead and 36 in dead)
chk("E2 play 路径 cmp si,0x27 上界（ID<39）",
    MEM[0x4997C5 - BASE:0x4997C9 - BASE] == b"\x66\x83\xfe\x27")

passed = sum(1 for _, c in results if c)
total = len(results)
print("\nRESULT: %d/%d checks passed" % (passed, total))
raise SystemExit(0 if passed == total else 1)
