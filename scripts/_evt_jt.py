# -*- coding: utf-8 -*-
"""Enumerate all jump-table dispatchers (jmp [reg*4 + imm]) over the code range,
resolve each table as both absolute and relative-to-table, and report any entry
that resolves to TARGET. Also report the table's entry count and value range."""
import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

TARGET = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x4e82c0
CODE_LO, CODE_HI = 0x400000, 0x600000

def va2off(va): return va - BASE

dispatchers = []
code = MEM[va2off(CODE_LO):va2off(CODE_HI)]
for ins in md.disasm(code, CODE_LO):
    if ins.mnemonic == 'jmp' and ins.operands:
        op = ins.operands[0]
        if op.type == X86_OP_MEM and op.mem.scale == 4 and op.mem.disp:
            tbl = op.mem.disp & 0xffffffff
            if CODE_LO <= tbl < CODE_HI:
                dispatchers.append((ins.address, tbl, ins.op_str))

print(f"found {len(dispatchers)} jump-table dispatchers")

for jmp_va, tbl, opstr in dispatchers:
    # read up to 256 entries (1024 bytes) from table
    to = va2off(tbl)
    if to + 1024 > len(MEM): 
        continue
    entries = struct.unpack('<256I', MEM[to:to+1024])
    abs_hits = []
    rel_hits = []
    valid_abs = 0
    for i, v in enumerate(entries):
        if CODE_LO <= v < CODE_HI:
            valid_abs += 1
            if v == TARGET:
                abs_hits.append(i)
        # relative-to-table: target = tbl + signed(v)
        rv = (v & 0xffffffff)
        if rv & 0x80000000:
            rv -= 0x100000000
        tgt = (tbl + rv) & 0xffffffff
        if CODE_LO <= tgt < CODE_HI:
            if tgt == TARGET:
                rel_hits.append((i, rv))
    if abs_hits or rel_hits:
        print(f"\n*** MATCH at jmp {jmp_va:#010x} table={tbl:#010x} ({opstr})")
        print(f"    absolute entries pointing to target: {abs_hits}")
        print(f"    relative-to-table entries: {rel_hits}")
    # heuristic: tables with >8 valid absolute entries are real dispatch tables
    if valid_abs > 8:
        print(f"  dispatch {jmp_va:#010x} table={tbl:#010x} valid_abs={valid_abs} first={entries[0]:#x}")
