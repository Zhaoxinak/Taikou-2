#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recon 5: search binary for an authoritative 27->8 item-category mapping table.
HYP mapping (data-driven): def-cat -> pool-cat(0..7)
 0..5(tea)->7, 6..10(weapon)->4, 11..13(book)->1, 14..17(treasure)->3,
 18..20(art)->6, 22..25(south)->5, 26(fabric)->2 ; cat21 empty.
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

import struct
IMG = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
# build pattern with wildcard at index 21
pat = [7,7,7,7,7,7, 4,4,4,4,4, 1,1,1, 3,3,3,3, 6,6,6, None, 5,5,5,5, 2]
print("pattern len", len(pat))
def match(buf, i):
    for k, v in enumerate(pat):
        if v is None: continue
        if buf[i+k] != v: return False
    return True
hits = []
for i in range(len(IMG) - len(pat)):
    if match(IMG, i):
        hits.append(i)
print("matches:", len(hits))
for h in hits:
    va = 0x400000 + h
    seg = IMG[h:h+len(pat)]
    print(f"  0x{va:x}: {list(seg)}")

# Also try reversed: maybe pool-cat -> how many def-cats, or a 27-entry word table.
# Try word-table: each entry 2 bytes, value 0..7 (low byte), high byte 0.
print("\n-- search 27-word table (each 2B, low=cat0..7, high=0) --")
word_pat = []
for v in pat:
    word_pat.append(struct.pack('<H', v if v is not None else 0))
# can't wildcard easily in bytes; do manual
wp = b''.join(word_pat)
# replace wildcard position with a don't-care by searching without it
# build 26-word search excluding index21
seq = []
for k, v in enumerate(pat):
    if v is None: continue
    seq.append(struct.pack('<H', v))
# need them contiguous; index21 missing breaks contiguity. Search two halves.
pre = b''.join(struct.pack('<H', v) for v in pat[:21])
post = b''.join(struct.pack('<H', v) for v in pat[22:])
hits2=[]
for i in range(len(IMG)-len(pre)):
    if IMG[i:i+len(pre)]==pre:
        j=i+len(pre)+2  # skip 1 word (cat21 wildcard)
        if IMG[j:j+len(post)]==post:
            hits2.append(i)
print("word-table matches:", len(hits2))
for h in hits2:
    va=0x400000+h
    print(f"  0x{va:x}: {[struct.unpack('<H',IMG[h+k*2:h+k*2+2])[0] for k in range(27)]}")
