#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""For each candidate SNDATA serializer, detect record-byte reads (small
displacement 0..48) and global-array writes (0x519xxx/0x52xxxx). Build the
field-offset -> entity-array map. Text-based scan for robustness."""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
import re

BASE = 0x400000
data = open("F:/Games/Taikou 2/scripts/_unpacked_mem.bin", "rb").read()
cs = Cs(CS_ARCH_X86, CS_MODE_32)

# candidate VAs from main parser call targets (read+write+helpers)
candidates = [0x47dae0,0x47db20,0x47dc40,0x47de60,0x47e090,0x47e1c0,0x47e340,
              0x47e3b0,0x47e420,0x47e4c0,0x47e5e0,0x47e6c0,0x47e7b0,0x47e8e0,
              0x47ead0,0x47eb50,0x47ec10,0x47ec90,0x47ed10,0x47ed50,0x47ed90,
              0x47edc0,0x47ee10,0x47ee80,0x47eed0,0x47ef20,0x47ef60,0x47efc0,
              0x47f060,0x47f090,0x47f0c0,0x47f130,0x47f1b0]
# Better: derive from call targets
calls=set()
for ins in cs.disasm(data[0x47f350-BASE:0x47f350-BASE+0x900],0x47f350):
    if ins.mnemonic=='call' and ins.op_str.startswith('0x'):
        t=int(ins.op_str,16)
        if 0x47dae0<=t<=0x47f300:
            calls.add(t)
candidates = sorted(calls)

disp_re = re.compile(r"\+0x([0-9a-f]+)\]")
glob_re = re.compile(r"(0x5[12][0-9a-f]{3})")

def analyze(va, window=0x280):
    code = data[va-BASE:va-BASE+window]
    rec_offsets=set()
    globals_ref=set()
    for ins in cs.disasm(code, va):
        s=f"{ins.mnemonic} {ins.op_str}"
        # record field reads: memory operand with small disp 0..48
        for m in disp_re.finditer(s):
            v=int(m.group(1),16)
            if 0<=v<=48:
                rec_offsets.add(v)
        # global refs
        for m in glob_re.finditer(s):
            globals_ref.add(int(m.group(1),16))
        if ins.mnemonic=='ret' and ins.address>va+0x40:
            break
    return sorted(rec_offsets), sorted(globals_ref)

print(f"candidates: {len(candidates)}")
results=[]
for va in candidates:
    offs, globs = analyze(va)
    # classify: a true field-mapping serializer reads record bytes AND touches globals
    if offs and globs:
        results.append((va, offs, globs))

print(f"\n=== {len(results)} field-mapping serializers ===\n")
for va, offs, globs in results:
    gstr = " ".join(f"0x{v:06x}" for v in globs[:10])
    print(f"0x{va:06x}:")
    print(f"   reads record offsets: {offs}")
    print(f"   global refs:          {gstr}")
