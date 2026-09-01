# -*- coding: utf-8 -*-
"""产出 dword[0x513b14] 对象的完整字段图: 函数体 + 调用点 ecx 偏移。"""
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
from collections import Counter, defaultdict
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
mem = open(MEM, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

LO, HI = 0x49A2C0, 0x49A5C0

targets = {}
for i in range(len(mem) - 5):
    if mem[i] != 0xE8:
        continue
    rel = struct.unpack_from("<i", mem, i + 1)[0]
    dst = (BASE + i + 5 + rel) & 0xFFFFFFFF
    if LO <= dst < HI:
        targets.setdefault(dst, []).append(BASE + i)

print("=" * 84)
print("A. 各入口函数体")
print("=" * 84)
for t in sorted(targets):
    o = t - BASE
    print(f"\n--- {t:08x}  (callers={len(targets[t])}) ---")
    for ins in md.disasm(mem[o:o + 56], t):
        print(f"  {ins.address:08x}  {ins.mnemonic:<8} {ins.op_str}")
        if ins.mnemonic == "ret":
            break

print("\n" + "=" * 84)
print("B. 每个调用点传入的 ecx 偏移 (lea/add ecx, [reg + N] 或 add ecx, N)")
print("=" * 84)


def ecx_off(addr):
    o = addr - BASE
    st = max(0, o - 40)
    seq = []
    for ins in md.disasm(mem[st:o], BASE + st):
        seq.append((ins.address, ins.mnemonic, ins.op_str))
    val = None
    for a, m, p in reversed(seq[-6:]):
        mm = re.match(r"lea\s+ecx,\s*\[(\w+) \+ (0x[0-9a-f]+|\d+)\]$", f"{m} {p}")
        if mm:
            val = int(mm.group(2), 0)
            break
        mm = re.match(r"add\s+ecx,\s*(0x[0-9a-f]+|\d+)$", f"{m} {p}")
        if mm:
            val = int(mm.group(1), 0)
            break
        if m == "mov" and p.startswith("ecx, dword ptr [0x"):
            val = 0
            break
    return val


per = defaultdict(Counter)
for t, sites in targets.items():
    for s in sites:
        per[t][ecx_off(s)] += 1
print(f"  {'入口':<12}{'ecx偏移 -> 次数'}")
for t in sorted(per):
    c = per[t]
    s = "  ".join(f"+{k:#x}" if k is not None else "?" for k in c.elements().__iter__() for _ in range(c[k]))[:80]
    print(f"  {t:#010x}  {dict((k if k is not None else '?', v) for k, v in c.items())}")

print("\n" + "=" * 84)
print("C. 汇总: 技能 setter 全表 (对象内绝对偏移)")
print("=" * 84)
BIT = {0xFC: 0, 0xF3: 2, 0xCF: 4, 0x3F: 6}
rows = []
for t in sorted(targets):
    o = t - BASE
    txt = []
    for ins in md.disasm(mem[o:o + 56], t):
        txt.append((ins.mnemonic, ins.op_str))
        if ins.mnemonic == "ret":
            break
    joined = " | ".join(f"{m} {p}" for m, p in txt)
    m2 = re.search(r"and al, (0x[0-9a-f]+|\d+)", joined)
    if not m2 or int(m2.group(1), 0) not in BIT:
        continue
    d = 0
    m1 = re.search(r"byte ptr \[ecx(?: \+ (0x[0-9a-f]+|\d+))?\]", joined)
    if m1 and m1.group(1):
        d = int(m1.group(1), 0)
    eoffs = [k for k in per[t] if k is not None]
    if not eoffs:
        continue
    eoff = Counter({k: per[t][k] for k in eoffs}).most_common(1)[0][0]
    rows.append((eoff + d, BIT[int(m2.group(1), 0)], t, eoff, d))
rows.sort()
SK = ["口才", "马术", "算术", "剑术", "忍术", "兵法", "洋枪", "筑城", "礼法", "茶道"]
print(f"  {'技能':<6}{'绝对偏移':>10}{'位':>6}{'setter':>12}{'ecx+':>7}{'disp':>6}")
for i, (abs_off, bit, t, eo, d) in enumerate(rows):
    nm = SK[i] if i < 10 else "?"
    print(f"  [{i}]{nm:<4}{abs_off:#010x}{bit:>6}{t:#010x}{eo:+#7x}{d:>6}")
print(f"\n  共 {len(rows)} 个 2-bit setter (期望 10)")
