# -*- coding: utf-8 -*-
"""枚举 0x49a400+ 的 2-bit 域 setter 全族 + e8 调用方。"""
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>

import re, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
mem = open(MEM, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

START, END = 0x49A400, 0x49A5C0

print("=" * 80)
print("A. setter 族枚举 (每条函数: 字节偏移 / 清位掩码 / 位移)")
print("=" * 80)
o = START - BASE
funcs = []          # (addr, byteoff, mask, shift)
cur_ins = []
for ins in md.disasm(mem[o:o + (END - START)], START):
    cur_ins.append((ins.address, ins.mnemonic, ins.op_str))
    if ins.mnemonic == "ret":
        txt = " | ".join(f"{m} {p}" for _, m, p in cur_ins)
        m1 = re.search(r"byte ptr \[ecx \+ (0x[0-9a-f]+|\d+)\]", txt)
        m2 = re.search(r"and al, (0x[0-9a-f]+|\d+)", txt)
        m3 = re.search(r"shl al, (0x[0-9a-f]+|\d+)", txt)
        if m1 and m2:
            by = int(m1.group(1), 0)
            mask = int(m2.group(1), 0)
            sh = int(m3.group(1), 0) if m3 else 0
            # 由掩码反推 bit 位
            bits = {0xFC: 0, 0xF3: 2, 0xCF: 4, 0x3F: 6}.get(mask)
            funcs.append((cur_ins[0][0], by, mask, sh, bits))
            print(f"  {cur_ins[0][0]:08x}  byte[+{by:#04x}]  mask={mask:#04x}  "
                  f"bit={bits}  shl={sh}   (n={len(cur_ins)} 条)")
        cur_ins = []
        continue
    if len(cur_ins) > 30:
        cur_ins = []

print(f"\n  共 {len(funcs)} 个 setter")
offmap = {}
for a, by, mask, sh, bits in funcs:
    offmap.setdefault(by, []).append((bits, a))
print("\n  按字节归并:")
for by in sorted(offmap):
    lst = sorted(offmap[by])
    print(f"    byte[+{by:#04x}]: bit位={[b for b, _ in lst]}  "
          f"入口={[hex(a) for _, a in lst]}")


def e8_callers(target):
    hits = []
    for i in range(len(mem) - 5):
        if mem[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", mem, i + 1)[0]
        if (BASE + i + 5 + rel) & 0xFFFFFFFF == target:
            hits.append(BASE + i)
    return hits


print("\n" + "=" * 80)
print("B. 各 setter 的 e8 调用方计数")
print("=" * 80)
allcall = {}
for a, by, mask, sh, bits in funcs:
    c = e8_callers(a)
    allcall[a] = c
    print(f"  {a:08x} (byte+{by:#04x} bit{bits}): {len(c)} 处  {[hex(x) for x in c[:6]]}")

tot = sorted({x for v in allcall.values() for x in v})
print(f"\n  去重调用点 {len(tot)} 处")

print("\n" + "=" * 80)
print("C. 调用点上下文 (前 12 处) —— 看 ecx 从哪来")
print("=" * 80)


def ctx(addr, back=18):
    o = addr - BASE
    st = max(0, o - 100)
    seq = []
    for ins in md.disasm(mem[st:o + 8], BASE + st):
        seq.append((ins.address, ins.mnemonic, ins.op_str))
    idx = next((k for k, s in enumerate(seq) if s[0] == addr), None)
    return seq[max(0, (idx or 0) - back): (idx or 0) + 3]


for a in tot[:12]:
    print(f"\n  --- call @ {a:08x} ---")
    for ad, m, p in ctx(a):
        mark = " <<<" if ad == a else ""
        print(f"    {ad:08x}  {m:<8} {p}{mark}")
