# -*- coding: utf-8 -*-
"""Scan image for runs of consecutive 4-byte values that are all valid code
addresses => candidate function-pointer / vtable / handler tables.
Report runs and whether TARGET is present."""
import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()
CODE_LO, CODE_HI = 0x401000, 0x4d0000
TARGET = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x4e82c0

def is_code(v):
    return CODE_LO <= v < CODE_HI

MIN_RUN = 6
i = 0
n = len(MEM) - 4
runs = []
start = None
cur = []
while i < n:
    v = struct.unpack('<I', MEM[i:i+4])[0]
    if is_code(v):
        if start is None:
            start = BASE + i
            cur = []
        cur.append((BASE+i, v))
    else:
        if start is not None and len(cur) >= MIN_RUN:
            runs.append((start, cur))
        start = None
        cur = []
    i += 4
if start is not None and len(cur) >= MIN_RUN:
    runs.append((start, cur))

print(f"total candidate runs (>= {MIN_RUN} code ptrs): {len(runs)}")
for start, cur in runs:
    vals = [v for _, v in cur]
    has_target = TARGET in vals
    flag = " <<< TARGET" if has_target else ""
    print(f"  run@{start:#010x} len={len(cur)} [{vals[0]:#x}..{vals[-1]:#x}]{flag}")
    if has_target:
        for off, v in cur:
            mark = "==>" if v == TARGET else "    "
            print(f"      {mark} {off:#010x}: {v:#010x}")
