# -*- coding: utf-8 -*-
"""Identify the new table 0x50cfa8 (stride 13) found in 续107 (ids 15/16/17).

Steps:
  1. raw hex dump around the base (and base-8..base+8 to catch ±1 folding)
  2. interpret as 13-byte records; try to spot repeating structure
  3. reverse-lookup every WORD against msgx_all_texts.json (续102 method)
  4. immediate-xref scan for the base (and base±1..±4) -> who reads/writes it
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

import io, sys, struct, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
CODE_LO, CODE_HI = 0x400000, 0x600000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
def off(va): return va - BASE

TBL = 0x50cfa8
STRIDE = 13

def dump(va, n=0x120, step=16):
    for i in range(0, n, step):
        row = MEM[off(va)+i: off(va)+i+step]
        hexs = ' '.join(f'{b:02x}' for b in row)
        asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in row)
        print(f"  {va+i:#08x}: {hexs:<47s} {asc}")

print(f"=== raw dump at {TBL:#x} (and the 8 bytes before, to catch base-1 folding) ===")
dump(TBL - 8, 0x130)

print(f"\n=== interpreted as {STRIDE}-byte records ===")
for r in range(12):
    rec = MEM[off(TBL)+r*STRIDE: off(TBL)+(r+1)*STRIDE]
    if not rec: break
    hexs = ' '.join(f'{b:02x}' for b in rec)
    # also show as words (little endian, unaligned) for pattern spotting
    ws = [struct.unpack_from('<H', rec, k)[0] for k in range(0, STRIDE-1, 2)]
    asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in rec)
    print(f"  rec[{r:2d}] @ {TBL+r*STRIDE:#08x}: {hexs}  | words={[f'{w:#x}' for w in ws]}  | {asc}")

# ---- reverse lookup against MSGX texts (续102 method) ----
msgx = {}
p = _ROOT + '/scripts/msgx_all_texts.json'
if os.path.exists(p):
    try:
        j = json.load(open(p, encoding='utf-8'))
        texts = j.get('texts', j)
        if isinstance(texts, list):
            msgx = {i: t for i, t in enumerate(texts)}
        elif isinstance(texts, dict):
            msgx = {int(k): v for k, v in texts.items()}
    except Exception as e:
        print(f"  (msgx load failed: {e})")
print(f"\n=== MSGX reverse lookup ({len(msgx)} texts loaded) ===")
if msgx:
    n = 14 * STRIDE
    blob = MEM[off(TBL): off(TBL)+n]
    hits = []
    for k in range(0, len(blob)-1):
        w = struct.unpack_from('<H', blob, k)[0]
        if w in msgx:
            t = msgx[w]
            t = t if isinstance(t, str) else str(t)
            hits.append((k, w, t[:40]))
    if hits:
        for k, w, t in hits[:40]:
            print(f"  off +{k:#x} (rec {k//STRIDE}, +{k%STRIDE}): id {w:#x} -> {t}")
        print(f"  total aligned-or-not hits: {len(hits)}")
    else:
        print("  no WORD in the first 14 records matches a MSGX id")

# ---- immediate xref for the base and base±1..±4 ----
print(f"\n=== immediate xref for {TBL:#x} (and base-1..base+4) ===")
targets = {TBL + d: d for d in (-4, -3, -2, -1, 0, 1, 2, 3, 4)}
fn_starts = set()
i = 0; n = len(MEM) - 5
while i < n:
    b = MEM[i]
    if b == 0xE8:
        rel = struct.unpack('<i', MEM[i+1:i+5])[0]
        tgt = (BASE + i + 5 + rel) & 0xffffffff
        if CODE_LO <= tgt < CODE_HI: fn_starts.add(tgt)
    elif b in (0xC3, 0xC2): fn_starts.add(BASE + i + 1)
    elif b == 0xE9:
        rel = struct.unpack('<i', MEM[i+1:i+5])[0]
        tgt = (BASE + i + 5 + rel) & 0xffffffff
        if tgt > BASE + i and CODE_LO <= tgt < CODE_HI: fn_starts.add(tgt)
    i += 1
k = 0
while True:
    p2 = MEM.find(b'\x55\x89\xe5', k)
    if p2 < 0: break
    fn_starts.add(BASE + p2); k = p2 + 1
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

found = {}
for fn in fn_list:
    nxt = fn_next[fn]
    if nxt - fn > 0x800: nxt = fn + 0x800
    for ins in disasm_fn(fn, nxt - fn):
        for o in ins.operands:
            v = None
            if o.type == CS_OP_IMM: v = o.imm & 0xffffffff
            elif o.type == CS_OP_MEM and o.mem.disp: v = o.mem.disp & 0xffffffff
            if v is None: continue
            for t, d in targets.items():
                if v == t:
                    found.setdefault((t, d), []).append((fn, ins.address, ins.mnemonic, ins.op_str))

for (t, d) in sorted(found):
    lst = found[(t, d)]
    print(f"\n  base{d:+d} = {t:#x}: {len(lst)} hit(s)")
    for fn, ad, m, ops in lst[:12]:
        print(f"     0x{ad:x} (in 0x{fn:x}): {m} {ops}")
if not found:
    print("  (no xref at all — table may be reached via a computed base)")
