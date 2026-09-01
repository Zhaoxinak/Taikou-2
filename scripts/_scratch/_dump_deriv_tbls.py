# -*- coding: utf-8 -*-
"""Dump the 3 derivation tables behind SECT_A (col,row) index helpers:
  0x43a410(x) = byte[x + 0x512f28]
  0x43a420(x) = word[x*4 + 0x503710]   (DIR8)
  0x43a440(x) = word[x*4 + 0x503712]   (SPAWN_TYPE_TBL)
Also dump raw windows so we can see table boundaries / neighbouring data.
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

import sys, io, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()

def u16(off):
    return struct.unpack_from('<H', MEM, off - BASE)[0]
def u8(off):
    return MEM[off - BASE]

def hexdump(off, n, label):
    print('\n==== %s  [%08x .. %08x] ====' % (label, off, off + n))
    for i in range(0, n, 16):
        chunk = MEM[off - BASE + i: off - BASE + i + 16]
        hexs = ' '.join('%02x' % b for b in chunk)
        asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print('%08x  %-48s  %s' % (off + i, hexs, asc))

# Big raw windows first
hexdump(0x512f00, 0x140, 'BYTE-TBL region (0x512f28 byte table lives here)')
hexdump(0x5036a0, 0x80, 'MOVE-TBLs 0x5036a0/..a8/..c0/..c8 (referenced by 0x438a60)')
hexdump(0x503700, 0x300, '0x503710 DIR8 / 0x503712 SPAWN_TYPE word tables region')

# Decode the word tables explicitly
print('\n==== DIR8  (0x43a420) word[x*4+0x503710], x=0..63 ====')
for x in range(0, 64):
    print('  DIR8[%2d] = %5d (0x%04x)' % (x, u16(0x503710 + x * 4), u16(0x503710 + x * 4)))

print('\n==== SPAWN_TYPE (0x43a440) word[x*4+0x503712], x=0..63 ====')
for x in range(0, 64):
    print('  SPAWN[%2d] = %5d (0x%04x)' % (x, u16(0x503712 + x * 4), u16(0x503712 + x * 4)))

print('\n==== BYTE-TBL (0x43a410) byte[x+0x512f28], x=0..63 ====')
for x in range(0, 64):
    print('  B[%2d] = %3d (0x%02x)' % (x, u8(0x512f28 + x), u8(0x512f28 + x)))
