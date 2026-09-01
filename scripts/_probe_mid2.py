# -*- coding: utf-8 -*-
"""扫第二方法表区段 0x49a900..0x49ae00 (覆盖实体 +0x1c..+0x1f dword)。"""
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

LO, HI = 0x49A900, 0x49AE00
targets = {}
for i in range(len(mem) - 5):
    if mem[i] != 0xE8:
        continue
    rel = struct.unpack_from("<i", mem, i + 1)[0]
    dst = (BASE + i + 5 + rel) & 0xFFFFFFFF
    if LO <= dst < HI:
        targets.setdefault(dst, []).append(BASE + i)

print("=" * 88)
print(f"A. 第二方法表 [{LO:#x},{HI:#x}) 入口 {len(targets)} 个")
print("=" * 88)
for t in sorted(targets):
    o = t - BASE
    body = []
    for ins in md.disasm(mem[o:o + 56], t):
        body.append((ins.address, ins.mnemonic, ins.op_str))
        if ins.mnemonic == "ret":
            break
    txt = " | ".join(f"{m} {p}" for _, m, p in body)
    print(f"\n  {t:#010x}  callers={len(targets[t]):<3}")
    for a, m, p in body:
        print(f"      {a:08x}  {m:<8} {p}")

print("\n" + "=" * 88)
print("B. 调用点: ecx 偏移 + push 常量")
print("=" * 88)


def ecx_off(addr):
    o = addr - BASE
    st = max(0, o - 44)
    seq = []
    for ins in md.disasm(mem[st:o], BASE + st):
        seq.append((ins.mnemonic, ins.op_str))
        if len(seq) > 8:
            seq.pop(0)
    for m, p in reversed(seq):
        mm = re.match(r"lea\s+ecx,\s*\[(\w+) \+ (0x[0-9a-f]+|\d+)\]$", f"{m} {p}")
        if mm:
            return int(mm.group(2), 0)
        mm = re.match(r"add\s+ecx,\s*(0x[0-9a-f]+|\d+)$", f"{m} {p}")
        if mm:
            return int(mm.group(1), 0)
        if m == "mov" and p.startswith("ecx, dword ptr [0x"):
            return 0
    return None


def push_imm(addr, k=3):
    o = addr - BASE
    st = max(0, o - 20)
    seq = []
    for ins in md.disasm(mem[st:o], BASE + st):
        seq.append((ins.mnemonic, ins.op_str))
    out = []
    for m, p in seq[-k:]:
        mm = re.match(r"push\s+(0x[0-9a-f]+|\d+)$", f"{m} {p}")
        if mm:
            out.append(int(mm.group(1), 0))
    return out


per = defaultdict(Counter)
parg = defaultdict(Counter)
for t, sites in targets.items():
    for s in sites:
        per[t][ecx_off(s)] += 1
        for v in push_imm(s):
            parg[t][v] += 1
print(f"  {'入口':<12}{'ecx偏移':<20}{'push 常量'}")
for t in sorted(targets):
    eo = ", ".join(f"+{k:#x}×{v}" if k is not None else f"?×{v}"
                   for k, v in Counter({k: v for k, v in per[t].items()}).most_common())
    pa = ", ".join(f"{k:#x}×{v}" for k, v in parg[t].most_common(4))
    print(f"  {t:#010x}  {eo:<20}{pa}")
