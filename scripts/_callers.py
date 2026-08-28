# -*- coding: utf-8 -*-
"""Find all `call rel32` sites targeting the given VAs (and their host funcs)."""
import sys, io, struct, bisect
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()
TEXT_START, TEXT_END = 0x401000, 0x4d0000

def all_calls():
    out = []
    i = 0
    while True:
        i = MEM.find(b'\xe8', i, TEXT_END - BASE)
        if i < 0:
            break
        rel = struct.unpack_from('<i', MEM, i + 1)[0]
        t = (i + BASE) + 5 + rel
        if TEXT_START <= t < TEXT_END:
            out.append((i + BASE, t))
        i += 1
    return out

CALLS = all_calls()
STARTS = sorted({t for _, t in CALLS})

def host(va):
    k = bisect.bisect_right(STARTS, va) - 1
    return STARTS[k] if k >= 0 else 0

if __name__ == '__main__':
    for a in sys.argv[1:]:
        tgt = int(a, 0)
        sites = [s for s, t in CALLS if t == tgt]
        print(f'\n=== callers of {tgt:#x}: {len(sites)} ===')
        for s in sites:
            print(f'   call @{s:#08x}   (host func {host(s):#x})')
