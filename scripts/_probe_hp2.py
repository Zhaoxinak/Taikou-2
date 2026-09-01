#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe 2: find where HP globals get their INITIAL value.
Approach A: address loaded into a register via 'mov r32, 0x514995/0x514835' (opcodes B8-BF).
Approach B: find stores to computed addresses in the 0x514900..0x5149ff block (base+offset).
Approach C: find 'mov word ptr [r32], ...' whose r32 was just loaded with one of the HP addrs.
"""
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

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

HP = {0x514995: "HP_A", 0x514835: "HP_B"}
ADDR = {va: va.to_bytes(4, "little") for va in HP}

# ---- Approach A: mov r32, imm32 == HP addr ----
print("===== Approach A: 'mov r32, 0x514995/0x514835' =====")
a_hits = []
for va in HP:
    ab = ADDR[va]
    pos = 0
    while True:
        idx = MEM.find(ab, pos)
        if idx < 0:
            break
        pos = idx + 1
        # preceding byte = opcode B8..BF
        if idx < 1:
            continue
        op = MEM[idx-1]
        if 0xB8 <= op <= 0xBF:
            reg = op - 0xB8
            regnames = ["eax","ecx","edx","ebx","esp","ebp","esi","edi"]
            a_hits.append((idx-1, regnames[reg], va))
            # disasm a window AFTER to see the store using that reg
            ctx = "\n".join(f"  {ins.address:#08x}: {ins.mnemonic} {ins.op_str}"
                            for ins in md.disasm(MEM[idx+3:idx+3+40], BASE+idx+3))[:600]
            print(f"\n@ off {idx-1:#08x} (va {BASE+idx-1:#08x}): mov {regnames[reg]}, 0x{va:08x}")
            print(ctx)
print(f"\nApproach A total: {len(a_hits)}")

# ---- Approach B/C: scan whole image for stores into 0x5149xx block via reg+disp ----
# We look for 'mov [reg+disp32], r16/r32' or 'mov [reg+disp8], ...' where reg+disp == HP addr.
# Simpler: find any instruction whose effective address we can compute. Use capstone detail.
print("\n===== Approach B: capstone detail scan for stores w/ effective addr in 0x514900..0x5149ff =====")
md2 = Cs(CS_ARCH_X86, CS_MODE_32)
md2.detail = True
store_ops = {"mov", "add", "sub", "and", "or", "xor", "inc", "dec", "cmp", "test"}
found = []
# Scan only the code-ish region. Image size:
N = len(MEM)
STEP = 0x2000
for start in range(0, N, STEP):
    data = MEM[start:start+STEP+32]
    for ins in md2.disasm(data, BASE+start):
        if ins.mnemonic not in store_ops:
            continue
        # need operands
        try:
            ops = ins.operands
        except Exception:
            continue
        for op in ops:
            if op.type == 2:  # memory
                m = op.mem
                base = m.base
                disp = m.disp
                # if base is a reg and disp points into block, or absolute (base=0) disp in block
                eff = None
                if m.base == 0 and m.index == 0:
                    eff = disp & 0xffffffff
                if eff is not None and 0x514900 <= eff <= 0x5149ff:
                    found.append((ins.address, ins.mnemonic, ins.op_str, eff))
                    break
# dedupe by address
seen = set()
for addr, mn, opstr, eff in found:
    if addr in seen:
        continue
    seen.add(addr)
    print(f"  {addr:#08x}: {mn} {opstr}   (eff=0x{eff:08x})")
print(f"\nApproach B total unique: {len(seen)}")
