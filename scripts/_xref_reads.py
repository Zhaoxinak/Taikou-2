# -*- coding: utf-8 -*-
"""
Exhaustive memory-access address enumerator over a call-graph closure.

Motivation (2026-08-27 lesson): every attempt to locate the terrain
attack/defense matrix by *guessing the table shape* failed (0x513a78 turned
out to be the runtime facility instance array, 0x5037b8 the weather-keep
probability table).  So: stop guessing.  Walk the whole call closure of the
damage routine and dump EVERY absolute memory address it touches, then look
at what is actually non-zero in the static image.

Usage:
    _xref_reads.py 0x42d270 [--depth 3] [--lo 0x500000] [--hi 0x510000]
    _xref_reads.py 0x42d270 --all          # no address filter, group by page
"""
import sys, io, struct, bisect, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()
TEXT_START, TEXT_END = 0x401000, 0x4d0000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

# ---------- function starts = all call rel32 targets ----------
_starts = None
def starts():
    global _starts
    if _starts is None:
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
        _starts = sorted(s)
    return _starts

def next_start(va):
    st = starts()
    k = bisect.bisect_right(st, va)
    return st[k] if k < len(st) else TEXT_END

# ---------- scan one function ----------
def scan(va):
    """returns (callees, [(insn_va, addr, mnem, op_str, is_write)])"""
    stop = next_start(va)
    if stop <= va or stop - va > 0x4000:
        stop = va + 0x400
    callees, hits = set(), []
    cur = va
    while cur < stop:
        chunk = MEM[cur - BASE: stop - BASE]
        n = 0
        for ins in md.disasm(chunk, cur):
            n += 1
            cur = ins.address + ins.size
            if ins.mnemonic == 'call' and ins.op_str.startswith('0x'):
                t = int(ins.op_str, 16)
                if TEXT_START <= t < TEXT_END:
                    callees.add(t)
            # writes: first operand is the memory one
            for k, o in enumerate(ins.operands):
                if o.type != X86_OP_MEM:
                    continue
                m = o.mem
                if m.disp == 0:
                    continue
                # skip pure stack frame refs
                if m.base in (X86_REG_ESP, X86_REG_EBP) and m.index == 0:
                    continue
                a = m.disp & 0xffffffff
                if not (0x400000 <= a < 0x600000):
                    continue
                is_w = (k == 0 and ins.mnemonic not in ('cmp', 'test', 'push'))
                hits.append((ins.address, a, ins.mnemonic, ins.op_str, is_w,
                             m.index != 0, m.scale))
            if cur >= stop:
                break
        if n == 0:
            cur += 1
    return callees, hits

def closure(root, depth):
    seen, frontier, all_hits = {root}, [root], []
    for d in range(depth + 1):
        nxt = []
        for f in frontier:
            cal, hits = scan(f)
            all_hits += [(f,) + h for h in hits]
            for c in cal:
                if c not in seen:
                    seen.add(c)
                    nxt.append(c)
        frontier = nxt
        if not frontier:
            break
    return seen, all_hits

def nz(a, n=32):
    o = a - BASE
    if not (0 <= o < len(MEM) - n):
        return None
    return MEM[o:o + n]

if __name__ == '__main__':
    args = sys.argv[1:]
    depth = 3
    lo, hi = 0x500000, 0x510000
    if '--depth' in args:
        k = args.index('--depth'); depth = int(args[k + 1], 0); args = args[:k] + args[k + 2:]
    if '--lo' in args:
        k = args.index('--lo'); lo = int(args[k + 1], 0); args = args[:k] + args[k + 2:]
    if '--hi' in args:
        k = args.index('--hi'); hi = int(args[k + 1], 0); args = args[:k] + args[k + 2:]
    allmode = '--all' in args
    if allmode:
        args.remove('--all')
    root = int(args[0], 0)

    funcs, hits = closure(root, depth)
    print(f'closure of {root:#x} depth={depth}: {len(funcs)} funcs, {len(hits)} abs mem refs')

    by_addr = collections.defaultdict(list)
    for f, iva, a, mn, ops, isw, indexed, scale in hits:
        by_addr[a].append((f, iva, mn, ops, isw, indexed, scale))

    if allmode:
        pages = collections.Counter(a >> 12 for a in by_addr)
        print('\n-- pages touched --')
        for p, c in sorted(pages.items()):
            print(f'  {p<<12:#08x}  {c} distinct addrs')

    print(f'\n-- absolute refs in [{lo:#x},{hi:#x}) --')
    for a in sorted(by_addr):
        if not (lo <= a < hi):
            continue
        raw = nz(a, 24)
        blob = raw.hex() if raw else '??'
        allz = raw is not None and not any(raw)
        tag = '  <ALL-ZERO>' if allz else ''
        idx = any(h[5] for h in by_addr[a])
        w = any(h[4] for h in by_addr[a])
        print(f'\n{a:#08x}  refs={len(by_addr[a])} {"INDEXED" if idx else "scalar "} '
              f'{"W" if w else "R"}{tag}')
        print(f'          bytes: {blob}')
        for f, iva, mn, ops, isw, ix, sc in by_addr[a][:6]:
            print(f'          @{iva:#08x} (in {f:#x})  {mn} {ops}')
