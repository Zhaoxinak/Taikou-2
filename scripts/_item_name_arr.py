# -*- coding: utf-8 -*-
"""Locate & verify the item NAME array 0x521080 (200 x 13B) found in 续111.

Serializer 0x47ed70 (S11):
    edi = 0x51e1f5        ; record cursor (base 0x51e1f0 + 4 = vptr skipped)
    ebx = 0x521080        ; NAME array cursor, advanced 13 bytes per record
    count = 0xc8 (200)
    per record: 13 x BYTE -> ebx++      (name)
                BYTE  -> edi-1  (0x51e1f4 = rec+4)
                BYTE  -> edi    (0x51e1f5 = rec+5)
                WORD  -> edi+1  (0x51e1f6 = rec+6)
                WORD  -> edi+3  (0x51e1f8 = rec+8)
                edi += 0xa              ; STRIDE 10
So: item table  = 0x51e1f0, stride 10, 200 slots
    item names  = 0x521080, stride 13, 200 entries   (parallel array!)
"""
import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()
CODE_LO, CODE_HI = 0x400000, 0x600000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
def off(va): return va - BASE

NAME = 0x521080
TBL = 0x51e1f0

def hexdump(va, n, step=16):
    for i in range(0, n, step):
        row = MEM[off(va)+i: off(va)+i+step]
        h = ' '.join(f'{b:02x}' for b in row)
        a = ''.join(chr(b) if 32 <= b < 127 else '.' for b in row)
        print(f"  {va+i:#08x}: {h:<47s} {a}")

print("=== static bytes at 0x521080 (item name array, 200 x 13B) ===")
hexdump(NAME, 0x80)

print("\n=== static bytes at 0x51e1f0 (item table, stride 10) ===")
hexdump(TBL, 0x60)

# ---- xref for 0x521080 and neighbours ----
targets = {}
for d in range(-8, 9):
    targets[NAME + d] = d
targets[TBL] = 'TBL'

fn_starts = set()
i = 0; n = len(MEM) - 5
while i < n:
    b = MEM[i]
    if b == 0xE8:
        rel = struct.unpack('<i', MEM[i+1:i+5])[0]
        t = (BASE + i + 5 + rel) & 0xffffffff
        if CODE_LO <= t < CODE_HI: fn_starts.add(t)
    elif b in (0xC3, 0xC2): fn_starts.add(BASE + i + 1)
    elif b == 0xE9:
        rel = struct.unpack('<i', MEM[i+1:i+5])[0]
        t = (BASE + i + 5 + rel) & 0xffffffff
        if t > BASE + i and CODE_LO <= t < CODE_HI: fn_starts.add(t)
    i += 1
k = 0
while True:
    p = MEM.find(b'\x55\x89\xe5', k)
    if p < 0: break
    fn_starts.add(BASE + p); k = p + 1
fn_list = sorted(fn_starts)
fn_next = {}
for kk in range(len(fn_list)):
    fn_next[fn_list[kk]] = fn_list[kk+1] if kk+1 < len(fn_list) else fn_list[kk] + 0x800

def disasm_fn(va, max_bytes):
    end = va + max_bytes; cur = va; out = []
    while cur < end:
        chunk = MEM[off(cur):off(end)]
        got = list(md.disasm(chunk, cur))
        if not got: cur += 1; continue
        for ins in got:
            if ins.address >= end: break
            out.append(ins)
        last = out[-1]; nxt = last.address + last.size
        cur = nxt if nxt > cur else cur + 1
    return out

print(f"\n=== immediate xref for 0x521080 (base-8..+8) and 0x51e1f0 ===")
hits = {}
for fn in fn_list:
    nxt = fn_next[fn]
    if nxt - fn > 0x800: nxt = fn + 0x800
    for ins in disasm_fn(fn, nxt - fn):
        for o in ins.operands:
            v = None
            if o.type == CS_OP_IMM: v = o.imm & 0xffffffff
            elif o.type == CS_OP_MEM and o.mem.disp: v = o.mem.disp & 0xffffffff
            if v is None: continue
            if v in targets:
                hits.setdefault(v, []).append((fn, ins.address, ins.mnemonic, ins.op_str))

for v in sorted(hits, key=lambda x: (x != TBL, x)):
    d = targets[v]
    lbl = f"0x521080{d:+d}" if isinstance(d, int) else "0x51e1f0(TBL)"
    print(f"\n  {lbl} = {v:#x}: {len(hits[v])} hit(s)")
    for fn, ad, m, ops in hits[v][:14]:
        print(f"     0x{ad:x} (in 0x{fn:x}): {m} {ops}")
if not hits:
    print("  (none)")
