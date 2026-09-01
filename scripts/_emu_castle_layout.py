#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emulate 0x47f350 up to the castle serializer 0x47e130 and dump the EXACT
per-record read pattern (caller address of each 0x47da10 primitive call).
This settles the 24-vs-26 bytes-per-castle question with ground truth."""
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

import struct, json
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UcError
import unicorn.x86_const as X

IMG = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
DISK = open(_ROOT + '/Taikou2 Original/SNDATA1.TR2', 'rb').read()
BASE = 0x400000
STACK = 0x800000; STACK_TOP = STACK + 0x20000
OBJ = 0x820000; SCRATCH = 0x840000; SCRATCH_END = 0x860000

SUB1 = [0x47dae0,0x47dce0,0x47e130,0x47e3a0]
SUB_LABEL = {a: 'S%d' % i for i, a in enumerate(SUB1)}
CASTLE = 0x47e130
STOP = 0x47e3a0

SPEC = {
    0x47f5b0:('n',0,0), 0x47ae80:('n',0,0), 0x4ebd60:('n',0,0),
    0x49a210:('n',4,0), 0x49a1c0:('n',4,0), 0x49a1f0:('n',4,0), 0x49a250:('n',4,0),
    0x492850:('str',0,0), 0x492800:('open',0,1), 0x492820:('n',0,0),
    0x4eb5c0:('mal',4,0), 0x4edfa0:('cp',0,0), 0x4edf70:('cp',0,0),
    0x4411b0:('rd',8,0), 0x441190:('rd2',0,0),
}

uc = Uc(UC_ARCH_X86, UC_MODE_32)
uc.mem_map(BASE, len(IMG), 7); uc.mem_write(BASE, IMG)
uc.mem_map(STACK, 0x20000, 7)
uc.mem_map(OBJ, 0x1000, 7)
uc.mem_map(SCRATCH, SCRATCH_END - SCRATCH, 7)
uc.mem_write(OBJ + 0x8c, struct.pack('<H', 0))
uc.reg_write(X.UC_X86_REG_ESP, STACK_TOP)
uc.reg_write(X.UC_X86_REG_ECX, OBJ)

fpos = 0; malloc_ptr = SCRATCH
in_castle = False
castle_reads = []          # list of (caller_va, byte)
loop_iter = -1
CASTLE_TAB = 0x51eb88
prev_recptr = None

def do_return(cleanup, value=None):
    esp = uc.reg_read(X.UC_X86_REG_ESP)
    ret = struct.unpack('<I', uc.mem_read(esp, 4))[0]
    esp += 4 + cleanup
    uc.reg_write(X.UC_X86_REG_ESP, esp)
    if value is not None:
        uc.reg_write(X.UC_X86_REG_EAX, value)
    uc.reg_write(X.UC_X86_REG_EIP, ret)

def hook_code(uc, address, size, ud):
    global fpos, malloc_ptr, in_castle, loop_iter, prev_recptr
    if address == STOP:
        uc.emu_stop(); return
    if address in SUB_LABEL:
        if address == CASTLE:
            in_castle = True
        return
    if address in SPEC:
        kind, clean, val = SPEC[address]
        if kind in ('n', 'str'):
            do_return(clean, 0); return
        if kind == 'open':
            do_return(clean, 1); return
        if kind == 'mal':
            p = malloc_ptr; malloc_ptr += 0x4000
            if malloc_ptr > SCRATCH_END: malloc_ptr = SCRATCH
            do_return(clean, p); return
        if kind == 'cp':
            esp = uc.reg_read(X.UC_X86_REG_ESP)
            d = struct.unpack('<I', uc.mem_read(esp + 4, 4))[0]
            s = struct.unpack('<I', uc.mem_read(esp + 8, 4))[0]
            n = struct.unpack('<I', uc.mem_read(esp + 0xc, 4))[0]
            if 0 < n < 0x10000 and s and d:
                try: uc.mem_write(d, uc.mem_read(s, n))
                except Exception: pass
            do_return(clean, 0); return
        if kind in ('rd', 'rd2'):
            esp = uc.reg_read(X.UC_X86_REG_ESP)
            buf = struct.unpack('<I', uc.mem_read(esp + 4, 4))[0]
            cnt = struct.unpack('<I', uc.mem_read(esp + 8, 4))[0]
            if fpos + cnt <= len(DISK):
                uc.mem_write(buf, DISK[fpos:fpos + cnt])
            fpos += cnt
            do_return(clean, cnt); return
    if address == 0x47da10 and in_castle:
        # caller = return address on top of stack
        esp = uc.reg_read(X.UC_X86_REG_ESP)
        caller = struct.unpack('<I', uc.mem_read(esp, 4))[0]
        # byte comes from stream; we don't need value, only pattern
        castle_reads.append(caller)
        return

uc.hook_add(UC_HOOK_CODE, hook_code)
try:
    uc.emu_start(0x47f350, 0)
except UcError as e:
    print('UC ERROR at EIP=0x%x:' % uc.reg_read(X.UC_X86_REG_EIP), e)

print('castle 0x47da10 calls total:', len(castle_reads))
if castle_reads:
    # group by caller sequence: find repeating period
    from collections import Counter
    c = Counter(castle_reads)
    print('\ndistinct callers (va, count):')
    for va, n in sorted(c.items()):
        print('  0x%x  %d' % (va, n))
    # first 3 records: find period by locating repeats of first caller
    first = castle_reads[0]
    idxs = [i for i, v in enumerate(castle_reads) if v == first]
    if len(idxs) >= 2:
        period = idxs[1] - idxs[0]
        print('\ndetected per-record read count =', period)
        print('records detected =', len(idxs))
        print('\nfirst record read pattern (caller va list):')
        for i, v in enumerate(castle_reads[:period]):
            print('  %2d  0x%x' % (i, v))
json.dump({'n': len(castle_reads), 'callers': castle_reads},
          open(_ROOT + '/scripts/_castle_layout.json', 'w'))
print('\nsaved scripts/_castle_layout.json')
