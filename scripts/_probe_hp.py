#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe: all writes/refs to duel HP globals 0x514995 (side A) / 0x514835 (side B).
Flat image: off = va - 0x400000.  Classify by 3 bytes preceding the 4-byte imm address.
Disassemble a context window before each STORE/dec to recover the init formula vs per-hit decrement.
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

import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', "rb").read()
BASE = 0x400000

TARGETS = {
    0x514995: "HP_A(我方体力)",
    0x514835: "HP_B(敌方体力)",
}

# byte patterns for the 4-byte immediate address (little endian)
ADDR_BYTES = {va: va.to_bytes(4, "little") for va in TARGETS}

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

def classify(pre3):
    """pre3 = bytes of (opcode, optional modrm, ...) preceding the 4-byte addr.
    The instruction is at offset (addr_off - 3): bytes = pre3[0..] + addr(4)."""
    if len(pre3) < 3:
        return None
    b0, b1, b2 = pre3[0], pre3[1], pre3[2]
    # 66 89 /r  -> store reg16 to [addr]  (modrm at pre3[2] = 05/0d/15/1d/25/2d/35/3d)
    if b0 == 0x66 and b1 == 0x89:
        return "STORE16(reg)"
    if b0 == 0x66 and b1 == 0x8b:
        return "LOAD16(reg)"
    if b0 == 0x66 and b1 == 0xc7:
        return "STORE16(imm)"
    if b0 == 0x66 and b1 == 0x01:
        return "ADD16"
    if b0 == 0x66 and b1 == 0x29:
        return "SUB16"
    if b0 == 0x66 and b1 == 0x81:
        return "AND/OR/SUB/CMP imm16"
    if b0 == 0x66 and b1 == 0xff and b2 in (0x0d, 0x15, 0x1d, 0x25, 0x2d, 0x35, 0x3d):
        return "INC/DEC16"
    if b0 == 0x83 and b1 == 0x3d:
        return "CMP imm8"
    if b0 == 0x81 and b1 == 0x3d:
        return "CMP dword imm32"
    if b0 == 0x68:
        return "PUSH imm32"
    if b0 == 0x66 and b1 == 0x3d:
        return "CMP16 imm16"
    return None

def disasm_at(off, nbytes=24):
    """Disassemble starting at off for up to nbytes, return lines."""
    try:
        data = MEM[off:off+nbytes]
        lines = []
        for ins in md.disasm(data, BASE + off):
            lines.append(f"  {ins.address:#08x}: {ins.mnemonic} {ins.op_str}")
            if len(lines) >= 12:
                break
        return "\n".join(lines)
    except Exception as e:
        return f"  (disasm err {e})"

results = {va: [] for va in TARGETS}
for va in TARGETS:
    ab = ADDR_BYTES[va]
    pos = 0
    while True:
        idx = MEM.find(ab, pos)
        if idx < 0:
            break
        pos = idx + 1
        # preceding 3 bytes
        if idx < 3:
            continue
        pre3 = MEM[idx-3:idx]
        cls = classify(pre3)
        if cls is None:
            continue
        va_off = idx
        # capture context: disasm from (idx-3 - 20) to show computation, but align roughly
        ctx_start = max(0, idx - 3 - 20)
        ctx = disasm_at(ctx_start, 40)
        results[va].append((va_off, cls, ctx))

out = []
for va in TARGETS:
    out.append(f"===== {TARGETS[va]} 0x{va:08x} : {len(results[va])} refs =====")
    for va_off, cls, ctx in results[va]:
        out.append(f"\n-- ref @ off {va_off:#08x} (va {BASE+va_off:#08x}) : {cls}")
        out.append(ctx)
    out.append("")

open(_ROOT + '/scripts/_hp.txt', "w", encoding="utf-8").write("\n".join(out))
print("WROTE _hp.txt ; refs:", {hex(v): len(results[v]) for v in TARGETS})
