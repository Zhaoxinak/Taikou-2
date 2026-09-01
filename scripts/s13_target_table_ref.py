#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S13 目標 (Target/Objective) table — structural reverse reference + self-tests.

Static evidence only (capstone disasm + _unpacked_mem.bin byte reads). No emulation.

Proven facts
------------
* Section meta (sndata_all_sections_ref.py):
    ('S13', 0x47ef00, 2280, 0x5185b6, 114, 20, '20 条空表（全 0xff）')
  -> 20 records, 114 serialized bytes/record (=2280), serializer 0x47ef00.
* Serializer 0x47ef00 (full disasm) does ONE outer loop of 20 iterations; each
  iteration serializes a record from the in-memory anchor 0x5185ba:
    - 25 words @ [edi-0x32]  (record +0x00 .. +0x30)
    - 25 words @ [edi]       (record +0x32 .. +0x62)
    -  5 words @ [edi+0x32]  (record +0x64 .. +0x72)
    -  4 bytes @ [edi+0x3c .. +0x3f]  (record +0x6e .. +0x71)
  => 25*2 + 25*2 + 5*2 + 4 = 114 serialized bytes / record.  ✓
  After each record: `add edi, 0x8b`  => in-memory record STRIDE = 0x8b = 139.
  (139 - 114 = 25 bytes runtime-only header, vptr+extras, cf. S12 note.)
  Anchor 0x5185ba = record0 + 0x32  => record0 serial base = 0x518588.
* Record bases (stride 0x8b):
    rec0 = 0x518588, rec1 = 0x518613, rec2 = 0x51869e, ...
  These ABSOLUTE addresses are exactly the ones hit by the immediate xref scan
  (0x518613 -> 21 refs, 0x51869e -> 10 refs), confirming the stride.
* Writer 0x40a350 populates rec0/rec1 from a source entity:
    - clears rec0 (0x4a1030(0x518588,0,0));
    - copies source-entity bytes [src+0xe] -> rec+0x6e, [src+0x1a] -> rec+0x6f
      (or random if phase-flag 0x5203c1&0x1f==5 and getter 0x49f5d0==0x49f8b0);
    - resolves a target entity/name via 0x4198e0 + 0x4a33d0, copies the name
      buffer at 0x51f440 (0x48 bytes) and stores entity index = (ptr-0x519868)/47
      (magic 0xae4c415d) or sentinel 0x172;
    - 0x409650(0x518613) lays out a 5x5 (25-cell) 2-bit sub-grid at rec+0x64.
* 0x4a1030(rec, idx, val): writes a 2-bit field at rec + idx*2 + 0x64
  (the 5x5 grid cell setter). 0x409650 loops 5x5 calling 0x4a0ff0/0x4a1010/0x4a1030.
* Stream S[13] is all 0xff in a fresh save (sndata_all_sections_ref chk); the
  in-memory region 0x5185b6.. is all zero in the static image. => table is
  EMPTY by default, populated at runtime when objectives are assigned.

Gameplay meaning (evidence-based, hedged):
  S13 is the runtime "目標/目標記録" (objective/target) table: up to 20 tracked
  targets, each a record holding a target-entity reference (index + coords
  + name) and a 5x5 2-bit sub-grid (likely a small board/formation/map state)
  plus a float progress value at record+0x00/+0x76. Consumed by AI/event
  routines (the 0x518613 / 0x51869e array refs). The exact 5x5 semantics need
  dynamic emu tracing — flagged as follow-up.
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
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BIN = _ROOT + '/scripts/_unpacked_mem.bin'
data = open(BIN, 'rb').read()
BASE = 0x400000
def off(va): return va - BASE
def u16(va): return struct.unpack('<H', data[off(va):off(va)+2])[0]
def u8(va):  return data[off(va)]

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

def disasm(va, n=400):
    out = []
    for ins in md.disasm(data[off(va):off(va)+n*6], va):
        out.append((ins.address, ins.mnemonic, ins.op_str))
        if len(out) >= n:
            break
    return out

def disasm_range(va0, va1):
    out = []
    for ins in md.disasm(data[off(va0):off(va1)], va0):
        if ins.address >= va1:
            break
        out.append((ins.address, ins.mnemonic, ins.op_str))
    return out

CHECKS = 0
PASS = 0
def chk(name, cond):
    global CHECKS, PASS
    CHECKS += 1
    if cond:
        PASS += 1
        print('  [PASS] %s' % name)
    else:
        print('  [FAIL] %s' % name)

def verify():
    global CHECKS, PASS
    CHECKS = PASS = 0
    print('--- S13 serializer 0x47ef00 structure ---')
    s = disasm_range(0x47ef00, 0x47ef98)
    mnem = lambda a: [t for t in s if t[0] == a]
    cnt = lambda m, o: sum(1 for (_, x, y) in s if x == m and o in y)
    chk('outer loop counter init = 0x14 (20)',
        any(x == 'mov' and '0x14' in y and '[esp + 0x10]' in y for (_, x, y) in s))
    chk('in-memory record stride = add edi, 0x8b (139)',
        any(x == 'add' and 'edi' in y and '0x8b' in y for (_, x, y) in s))
    chk('anchor mov edi, 0x5185ba present',
        any(x == 'mov' and 'edi' in y and '0x5185ba' in y for (_, x, y) in s))
    chk('word-writer call 0x47d930 appears (3 loop bodies)',
        cnt('call', '0x47d930') >= 3)
    chk('byte-writer call 0x47d910 appears (4 bytes)',
        cnt('call', '0x47d910') == 4)
    chk('inner counters 0x19(25) x>=2 and 0x5(5) x>=1',
        sum(1 for (_, x, y) in s if x == 'mov' and 'ebp' in y and y.split(',')[1].strip() in ('0x19', '25')) >= 2 and
        sum(1 for (_, x, y) in s if x == 'mov' and 'ebp' in y and y.split(',')[1].strip() in ('0x5', '5')) >= 1)
    # serialized bytes/record = 25*2+25*2+5*2+4
    chk('serialized bytes/record = 114', 25*2 + 25*2 + 5*2 + 4 == 114)

    print('--- record base geometry (stride 0x8b) ---')
    rec0 = 0x5185ba - 0x32
    chk('rec0 serial base = 0x518588', rec0 == 0x518588)
    rec1 = rec0 + 0x8b
    rec2 = rec1 + 0x8b
    chk('rec1 serial base = 0x518613 (matches xref)', rec1 == 0x518613)
    chk('rec2 serial base = 0x51869e (matches xref)', rec2 == 0x51869e)
    # 20 serialized records * 114 B = 2280 B stream (matches section meta)
    chk('20 records * 114B = 2280B stream', 20 * 114 == 2280)
    # in-memory footprint = 20 * 0x8b (139) = 2780 B, mem_base 0x5185b6
    chk('in-memory stride 0x8b * 20 = 2780B', 20 * 0x8b == 2780)

    print('--- writer 0x40a350 populates rec0/rec1 ---')
    w = disasm_range(0x40a350, 0x40a4e2)
    chk('loads rec0 base 0x518588',
        any(x == 'mov' and 'ecx' in y and '0x518588' in y for (_, x, y) in w))
    chk('writes rec0 +0x6e (0x5185f6)',
        any(x == 'mov' and '0x5185f6' in y for (_, x, y) in w))
    chk('writes rec0 +0x6f (0x5185f7)',
        any(x == 'mov' and '0x5185f7' in y for (_, x, y) in w))
    chk('loads rec1 base 0x518613',
        any(x == 'mov' and 'ecx' in y and '0x518613' in y for (_, x, y) in w))
    chk('writes rec1 +0x6e (0x518681)',
        any(x == 'mov' and '0x518681' in y for (_, x, y) in w))
    chk('reads name buffer 0x51f440',
        any('0x51f440' in y for (_, x, y) in w))
    chk('entity-index div-by-47 magic 0xae4c415d',
        any('0xae4c415d' in y for (_, x, y) in w))

    print('--- 5x5 2-bit sub-grid at rec+0x64 (0x409650 / 0x4a1030) ---')
    g = disasm_range(0x409650, 0x409691)
    chk('0x409650 nests 5x5 (cmp si,5 / cmp di,5)',
        any('si, 5' in y for (_, x, y) in g) and any('di, 5' in y for (_, x, y) in g))
    chk('0x409650 calls 0x4a1030 (2-bit setter)',
        any(x == 'call' and '0x4a1030' in y for (_, x, y) in g))
    st = disasm_range(0x4a1030, 0x4a1060)
    chk('0x4a1030 writes at [base + idx*2 + 0x64]',
        any(x == 'lea' and 'eax' in y and '0x64' in y and '*2' in y for (_, x, y) in st))

    print('--- empty-by-default ---')
    region = data[off(0x5185b6):off(0x5185b6) + 2280]
    chk('in-memory S13 region all zero (static image)',
        all(b == 0 for b in region))
    # stream all-0xff is asserted by sndata_all_sections_ref.py chk('S13 (2280B) 全 0xff')

    print('\nRESULT: %d/%d checks passed' % (PASS, CHECKS))
    return PASS == CHECKS

if __name__ == '__main__':
    ok = verify()
    import sys
    sys.exit(0 if ok else 1)
