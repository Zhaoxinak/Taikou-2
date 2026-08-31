# -*- coding: utf-8 -*-
"""横扫方法表剩余区段 0x49a5f0..0x49a8b0: 入口 / 函数体 / ecx 偏移 / 常量参数。"""
import re, struct
from collections import Counter, defaultdict
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
mem = open(MEM, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

LO, HI = 0x49A5F0, 0x49A8C0

targets = {}
for i in range(len(mem) - 5):
    if mem[i] != 0xE8:
        continue
    rel = struct.unpack_from("<i", mem, i + 1)[0]
    dst = (BASE + i + 5 + rel) & 0xFFFFFFFF
    if LO <= dst < HI:
        targets.setdefault(dst, []).append(BASE + i)

print("=" * 88)
print(f"A. 入口清单 [{LO:#x},{HI:#x}) —— 共 {len(targets)} 个")
print("=" * 88)

BITS = {0xFC: "b0-1", 0xF3: "b2-3", 0xCF: "b4-5", 0x3F: "b6-7",
        0xFE: "b0", 0xFD: "b1", 0xFB: "b2", 0xF7: "b3",
        0xEF: "b4", 0xDF: "b5", 0xBF: "b6", 0x7F: "b7",
        0xF0: "lo-nibble", 0x0F: "hi-nibble"}

bodies = {}
for t in sorted(targets):
    o = t - BASE
    body = []
    for ins in md.disasm(mem[o:o + 64], t):
        body.append((ins.address, ins.mnemonic, ins.op_str))
        if ins.mnemonic == "ret":
            break
    bodies[t] = body
    txt = " | ".join(f"{m} {p}" for _, m, p in body)
    # 写入目标
    w = re.search(r"mov\s+(byte|word|dword) ptr \[ecx(?: \+ (0x[0-9a-f]+|\d+))?\], (\w+)", txt)
    mask = re.search(r"and\s+(?:al|ax|eax|dl|dx|edx),\s*(0x[0-9a-f]+|\d+)", txt)
    cmpv = re.search(r"cmp\s+(?:ax|al|eax|dx),\s*(0x[0-9a-f]+|\d+)", txt)
    movret = re.search(r"mov\s+eax,\s*(0x[0-9a-f]+)", txt)
    disp = int(w.group(2), 0) if w and w.group(2) else (0 if w else None)
    print(f"  {t:08x} ncall={len(targets[t]):<3}", end="")
    if w:
        print(f" 写{w.group(1):>5}[ecx{'+' + hex(disp) if disp else ''}]<={w.group(3)}", end="")
    if mask:
        print(f"  mask={mask.group(1)}", end="")
    if cmpv:
        print(f"  cmp={cmpv.group(1)}", end="")
    if movret and not w:
        print(f"  ret={movret.group(1)}", end="")
    print()
    if not w and not movret:
        print(f"        {txt[:96]}")

print("\n" + "=" * 88)
print("B. 调用点: ecx 偏移 + push 的常量参数")
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


def push_imm_before(addr):
    """调用前 3 条内的 push imm。"""
    o = addr - BASE
    st = max(0, o - 20)
    seq = []
    for ins in md.disasm(mem[st:o], BASE + st):
        seq.append((ins.mnemonic, ins.op_str))
    out = []
    for m, p in seq[-3:]:
        mm = re.match(r"push\s+(0x[0-9a-f]+|\d+)$", f"{m} {p}")
        if mm:
            out.append(int(mm.group(1), 0))
    return out


per = defaultdict(Counter)
pargs = defaultdict(Counter)
for t, sites in targets.items():
    for s in sites:
        per[t][ecx_off(s)] += 1
        for v in push_imm_before(s):
            pargs[t][v] += 1

print(f"  {'入口':<12}{'ecx偏移(次数)':<26}{'push 常量(次数)'}")
for t in sorted(targets):
    eo = ", ".join(f"+{k:#x}×{v}" if k is not None else f"?×{v}"
                   for k, v in Counter({k: v for k, v in per[t].items()}).most_common())
    pa = ", ".join(f"{k:#x}×{v}" for k, v in pargs[t].most_common(4))
    print(f"  {t:#010x}  {eo:<26}{pa}")
