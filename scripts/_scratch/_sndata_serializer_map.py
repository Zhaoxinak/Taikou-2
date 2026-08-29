#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Map SNDATA 49B record fields by scanning the 16 read-serializer functions.

Each read serializer (0x47dae0..0x47f1b0, 16 of them) reads a range of the
49-byte record and writes into a global entity array. We disassemble each and
collect: (a) byte-offset reads within the record [0:49], (b) global store
targets (0x52xxxx / 0x519xxx). This yields the authoritative field map.
"""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x400000
data = open("F:/Games/Taikou 2/scripts/_unpacked_mem.bin", "rb").read()
cs = Cs(CS_ARCH_X86, CS_MODE_32)
cs.detail = True

# Read serializers are reported at 0x47dae0.. (16 types). Each ~0x? apart.
# We don't know exact spacing; scan a region and detect function prologues
# (push ebp / mov ebp,esp / sub esp) within 0x47dae0..0x47f1b0.
import struct
start_va = 0x47dae0
end_va = 0x47f1c0

# Find function starts = addresses where a 'call' lands, or prologue patterns.
# Simpler: collect all 'call' targets within region (the 16 serializers are
# called by main parser 0x47f350) then disassemble each a fixed window.
prologue_hits = []
chunk = data[start_va-BASE:end_va-BASE]
# detect 'push ebp; mov ebp,esp' (55 89 E5) or 'mov edi,edi; push ebp'(8B FF 55 89 E5)
i = 0
while i < len(chunk)-4:
    b = chunk[i:i+4]
    if b == b"\x55\x89\xe5" or b == b"\x8b\xff\x55\x89\xe5" or b[0:2]==b"\x55\x8b" :
        prologue_hits.append(start_va + i)
        i += 1
        continue
    i += 1

print(f"prologue candidates in region: {len(prologue_hits)}")
for va in prologue_hits[:40]:
    print(f"  0x{va:06x}")

def analyze_serializer(va, window=0x200):
    code = data[va-BASE:va-BASE+window]
    rec_offsets = set()
    globals_written = set()
    globals_read = set()
    for ins in cs.disasm(code, va):
        # record byte reads: movzx/mov al/ax, [reg + disp] where reg is the record base
        # Heuristic: any memory operand with a displacement in [0,49] and base reg
        for op in ins.operands:
            if op.type == 2:  # memory
                disp = op.mem.disp
                if 0 <= disp <= 48:
                    rec_offsets.add(disp)
                # global store/read targets
                if op.mem.base == 5 or (op.mem.base == 0 and op.mem.segment==0):
                    # absolute-ish; capstone gives disp as absolute when no base
                    pass
        # global writes: mov [0x52xxxx], ...
        s = f"{ins.mnemonic} {ins.op_str}"
        import re
        for m in re.finditer(r"0x5[0-9a-f]{4}", s):
            val = int(m.group(0),16)
            if 0x519000 <= val <= 0x52ffff:
                if ins.mnemonic in ("mov","movzx") and ("]" in s.split(",")[0] if "," in s else False):
                    pass
                # crude: record any 0x52xxxx / 0x519xxx mention
                globals_written.add(("W",val)) if ("]" in s and s.index("0x5")<s.index("]")) else globals_read.add(("R",val))
    return sorted(rec_offsets), sorted(globals_written), sorted(globals_read)

print("\n=== serializer analysis (record-offsets read, global targets) ===")
for va in prologue_hits[:20]:
    offs, gw, gr = analyze_serializer(va)
    if offs or gw or gr:
        print(f"\n0x{va:06x}:")
        print(f"   record byte offsets read: {offs}")
        print(f"   global WRITES: {[f'0x{v:06x}' for _,v in gw][:8]}")
        print(f"   global READS:  {[f'0x{v:06x}' for _,v in gr][:8]}")
