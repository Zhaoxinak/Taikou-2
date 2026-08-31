#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emulate 0x47f350 and dump the EXACT decoded stream bytes consumed by every
serializer, in read order, labelled by section.

Key point: 0x47da10 is NOT stubbed -- it executes for real, so the data flow is
faithful. We only *observe* it: at entry, ecx = stream object, [ecx+0x9a] is the
cursor and [ecx+0x94] the xor key, so decoded = mem[cursor] ^ key.
This removes all offset guessing: we get the real byte sequence per section.
"""
import struct, json
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UcError
import unicorn.x86_const as X

IMG = open('scripts/_unpacked_mem.bin', 'rb').read()
DISK = open('F:/Games/Taikou 2/Taikou2 Original/SNDATA1.TR2', 'rb').read()
BASE = 0x400000
STACK = 0x800000; STACK_TOP = STACK + 0x20000
OBJ = 0x820000; SCRATCH = 0x840000; SCRATCH_END = 0x860000

SUB1 = [0x47dae0, 0x47dce0, 0x47e130, 0x47e3a0, 0x47e440, 0x47e5a0, 0x47e770,
        0x47ea80, 0x47ebb0, 0x47ecb0, 0x47ed10, 0x47ed70, 0x47ee50, 0x47ef00,
        0x47f050, 0x47f0a0, 0x47f1b0, 0x47f210]
SUB_LABEL = {a: 'S%d' % i for i, a in enumerate(SUB1)}

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
uc.mem_write(OBJ + 0x8c, struct.pack('<H', 0))   # mode = store/load
uc.reg_write(X.UC_X86_REG_ESP, STACK_TOP)
uc.reg_write(X.UC_X86_REG_ECX, OBJ)

fpos = 0; malloc_ptr = SCRATCH
cur_section = 'PRE'
sections = {}      # section -> bytearray(decoded bytes, in read order)


def do_return(cleanup, value=None):
    esp = uc.reg_read(X.UC_X86_REG_ESP)
    ret = struct.unpack('<I', uc.mem_read(esp, 4))[0]
    esp += 4 + cleanup
    uc.reg_write(X.UC_X86_REG_ESP, esp)
    if value is not None:
        uc.reg_write(X.UC_X86_REG_EAX, value)
    uc.reg_write(X.UC_X86_REG_EIP, ret)


def hook_code(uc, address, size, ud):
    global fpos, malloc_ptr, cur_section
    if address in SUB_LABEL:
        cur_section = SUB_LABEL[address]
        sections.setdefault(cur_section, bytearray())
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
            # Partial reads at EOF must still copy what IS available, otherwise
            # the final 0x2000 chunk silently stays zero-filled (false "tail of
            # zeros"). Zero-fill the remainder, like a short read would.
            n = min(cnt, max(0, len(DISK) - fpos))
            if n > 0:
                uc.mem_write(buf, DISK[fpos:fpos + n])
            if n < cnt and 0 < cnt < 0x100000:
                try: uc.mem_write(buf + n, b'\x00' * (cnt - n))
                except Exception: pass
            fpos += cnt
            do_return(clean, cnt); return
    if address == 0x47da10:
        # ecx = stream object; [ecx+0x9a] = cursor into the buffer.
        # NOTE: 0x47d960 (refill) already XOR-decrypts each 0x2000 chunk in
        # place, so the byte at the cursor is ALREADY decoded -- do NOT xor again.
        ecx = uc.reg_read(X.UC_X86_REG_ECX)
        cur = struct.unpack('<I', uc.mem_read(ecx + 0x9a, 4))[0]
        already_decoded = uc.mem_read(cur, 1)[0]
        sections.setdefault(cur_section, bytearray()).append(already_decoded)
        return


uc.hook_add(UC_HOOK_CODE, hook_code)
try:
    uc.emu_start(0x47f350, 0x47f4d0)
except UcError as e:
    print('UC ERROR at EIP=0x%x:' % uc.reg_read(X.UC_X86_REG_EIP), e)

print('%-6s %8s' % ('sect', 'bytes'))
stream = bytearray()
for i in range(len(SUB1)):
    b = sections.get('S%d' % i, bytearray())
    print('S%-5d %8d' % (i, len(b)))
    stream += b
print('TOTAL  %8d' % len(stream))
open('scripts/_stream_dump.bin', 'wb').write(bytes(stream))
with open('scripts/_stream_sections.json', 'w') as f:
    json.dump({'sections': [{'name': 'S%d' % i,
                             'func': '0x%x' % SUB1[i],
                             'len': len(sections.get('S%d' % i, bytearray()))}
                            for i in range(len(SUB1))]}, f, indent=1)
print('saved scripts/_stream_dump.bin + _stream_sections.json')
