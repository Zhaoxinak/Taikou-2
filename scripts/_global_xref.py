# -*- coding: utf-8 -*-
"""
Global reverse index: absolute-address -> referencing instructions.

Disassembles every function (boundaries = all `call rel32` targets) once and
records every memory operand that carries an absolute displacement in
[0x400000,0x600000).  Then answers queries.

Usage:
    _global_xref.py 0x512868 [0x512b60 ...]        # who touches these
    _global_xref.py --range 0x503000 0x504000      # what is touched in a window
    _global_xref.py --func 0x43d000                # (debug) refs inside one func
"""
import sys, io, struct, bisect, collections, pickle, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()
TEXT_START, TEXT_END = 0x401000, 0x4d0000
CACHE = 'scripts/_global_xref.cache'
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def func_starts():
    s, i = set(), 0
    while True:
        i = MEM.find(b'\xe8', i, TEXT_END - BASE)
        if i < 0:
            break
        rel = struct.unpack_from('<i', MEM, i + 1)[0]
        t = (i + BASE) + 5 + rel
        if TEXT_START <= t < TEXT_END:
            s.add(t)
        i += 1
    return sorted(s)


def build():
    st = func_starts()
    st_end = st + [TEXT_END]
    idx = collections.defaultdict(list)   # addr -> [(func, iva, mnem, ops, w, indexed, scale)]
    for k, va in enumerate(st):
        stop = min(st_end[k + 1], va + 0x4000)
        cur = va
        while cur < stop:
            chunk = MEM[cur - BASE: stop - BASE]
            n = 0
            for ins in md.disasm(chunk, cur):
                n += 1
                cur = ins.address + ins.size
                for j, o in enumerate(ins.operands):
                    if o.type != X86_OP_MEM:
                        continue
                    m = o.mem
                    if m.disp == 0:
                        continue
                    if m.base in (X86_REG_ESP, X86_REG_EBP) and m.index == 0:
                        continue
                    a = m.disp & 0xffffffff
                    if not (0x400000 <= a < 0x600000):
                        continue
                    w = (j == 0 and ins.mnemonic not in ('cmp', 'test', 'push'))
                    idx[a].append((va, ins.address, ins.mnemonic, ins.op_str,
                                   w, m.index != 0, m.scale))
                if cur >= stop:
                    break
            if n == 0:
                cur += 1
    return dict(idx), st


def load():
    if os.path.exists(CACHE):
        with open(CACHE, 'rb') as f:
            return pickle.load(f)
    d = build()
    with open(CACHE, 'wb') as f:
        pickle.dump(d, f)
    return d


def show(idx, a):
    refs = idx.get(a, [])
    raw = MEM[a - BASE: a - BASE + 24]
    print(f'\n=== {a:#08x}  refs={len(refs)}  bytes={raw.hex()}'
          f'{"  <ALL-ZERO>" if not any(raw) else ""}')
    for f, iva, mn, ops, w, ix, sc in refs:
        print(f'   {"W" if w else "R"} @{iva:#08x} (func {f:#x})  {mn} {ops}')


if __name__ == '__main__':
    idx, st = load()
    args = sys.argv[1:]
    if not args:
        print(f'index: {len(idx)} distinct addrs, {len(st)} funcs')
        sys.exit()
    if args[0] == '--range':
        lo, hi = int(args[1], 0), int(args[2], 0)
        for a in sorted(idx):
            if lo <= a < hi:
                show(idx, a)
    elif args[0] == '--func':
        f0 = int(args[1], 0)
        for a in sorted(idx):
            for r in idx[a]:
                if r[0] == f0:
                    print(f'{a:#08x}  {r[2]} {r[3]}   @{r[1]:#x}')
                    break
    else:
        for a in args:
            show(idx, int(a, 0))
