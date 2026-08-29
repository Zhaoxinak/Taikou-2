# -*- coding: utf-8 -*-
"""Byte-level caller scanner: find every `E8 rel32` (call near) whose computed
target equals one of TARGETS, across the whole 2MB image. Fast, no linear disasm."""
import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()

TARGETS = [int(a,16) for a in sys.argv[1:]] if len(sys.argv)>1 else [0x49b860,0x4e84b0,0x49f6b0,0x44e280,0x4e82c0]
target_set = set(TARGETS)

def find_callers(target):
    out = []
    i = 0
    n = len(MEM) - 5
    while i < n:
        if MEM[i] == 0xE8:
            rel = struct.unpack('<i', MEM[i+1:i+5])[0]
            va = BASE + i
            tgt = (va + 5 + rel) & 0xffffffff
            if tgt == target:
                out.append(va)
        i += 1
    return out

if __name__ == '__main__':
    for t in TARGETS:
        cs = find_callers(t)
        print(f"=== callers of {t:#010x} ({len(cs)}) ===")
        for a in sorted(cs):
            print(f"  {a:#010x}")
