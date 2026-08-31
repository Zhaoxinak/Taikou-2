#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emulate SNDATA loader 0x47f350 under Unicorn; trace every object byte read
(0x47da10) with its absolute on-disk offset, labeled by active sub-loader.
Stubbed funcs return precisely per their real `ret N` cleanup."""
import struct
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UcError
import unicorn.x86_const as X

IMG = open('scripts/_unpacked_mem.bin','rb').read()
DISK = open('F:/Games/Taikou 2/Taikou2 Original/SNDATA1.TR2','rb').read()
assert len(DISK) == 40856, len(DISK)

BASE = 0x400000
STACK = 0x800000; STACK_TOP = STACK + 0x20000
OBJ = 0x820000; SCRATCH = 0x840000; SCRATCH_END = 0x860000

SUB1 = [0x47dae0,0x47dce0,0x47e130,0x47e3a0,0x47e440,0x47e5a0,0x47e770,0x47ea80,
        0x47ebb0,0x47ecb0,0x47ed10,0x47ed70,0x47ee50,0x47ef00,0x47f050,0x47f0a0,0x47f1b0,0x47f210]
SUB2 = [0x47dba0,0x47df00,0x47e260,0x47e3f0,0x47e4e0,0x47e680,0x47e8a0,0x47eb10,
        0x47ec30,0x47ece0,0x47ed40,0x47ede0,0x47eea0,0x47efa0,0x47f070,0x47f110,0x47f1e0,0x47f2a0]
SUB_LABEL = {a:'S%d'%i for i,a in enumerate(SUB1)}
SUB_LABEL.update({a:'P2_%d'%i for i,a in enumerate(SUB2)})

# addr -> (kind, ret_cleanup_bytes, return_value_for_simple)
# kind: 'n' noop, 'str' strcmp->equal, 'open'->1, 'mal' malloc, 'cp' memcpy,
#       'rd' single-block read (0x4411b0), 'rd2' bulk read (0x441190)
SPEC = {
    0x47f5b0:('n',0,0), 0x47ae80:('n',0,0), 0x4ebd60:('n',0,0),
    0x49a210:('n',4,0),0x49a1c0:('n',4,0),0x49a1f0:('n',4,0),0x49a250:('n',4,0),
    0x492850:('str',0,0), 0x492800:('open',0,1), 0x492820:('n',0,0),
    0x4eb5c0:('mal',4,0), 0x4edfa0:('cp',0,0), 0x4edf70:('cp',0,0),
    0x4411b0:('rd',8,0), 0x441190:('rd2',0,0),
}

uc = Uc(UC_ARCH_X86, UC_MODE_32)
uc.mem_map(BASE, len(IMG), 7)
uc.mem_write(BASE, IMG)
uc.mem_map(STACK, 0x20000, 7)
uc.mem_map(OBJ, 0x1000, 7)
uc.mem_map(SCRATCH, SCRATCH_END-SCRATCH, 7)
uc.mem_write(OBJ+0x8c, struct.pack('<H',0))
uc.reg_write(X.UC_X86_REG_ESP, STACK_TOP)
uc.reg_write(X.UC_X86_REG_ECX, OBJ)

fpos = 0
malloc_ptr = SCRATCH
cur_section = 'HEADER'
trace = []
read_1byte = 0
obj_count = 0
obj_start = None

def do_return(cleanup, value=None):
    esp = uc.reg_read(X.UC_X86_REG_ESP)
    ret = struct.unpack('<I', uc.mem_read(esp,4))[0]
    esp += 4 + cleanup
    uc.reg_write(X.UC_X86_REG_ESP, esp)
    if value is not None: uc.reg_write(X.UC_X86_REG_EAX, value)
    uc.reg_write(X.UC_X86_REG_EIP, ret)

def hook_code(uc, address, size, ud):
    global fpos, cur_section, malloc_ptr, read_1byte
    if address in SUB_LABEL:
        cur_section = SUB_LABEL[address]; return
    if address in SPEC:
        kind, clean, val = SPEC[address]
        if kind == 'n':
            do_return(clean, 0); return
        if kind == 'str':
            do_return(clean, 0); return
        if kind == 'open':
            do_return(clean, 1); return
        if kind == 'mal':
            p = malloc_ptr; malloc_ptr += 0x4000
            if malloc_ptr > SCRATCH_END: malloc_ptr = SCRATCH
            do_return(clean, p); return
        if kind == 'cp':
            esp = uc.reg_read(X.UC_X86_REG_ESP)
            d = struct.unpack('<I', uc.mem_read(esp+4,4))[0]
            s = struct.unpack('<I', uc.mem_read(esp+8,4))[0]
            n = struct.unpack('<I', uc.mem_read(esp+0xc,4))[0]
            if 0 < n < 0x10000 and s and d:
                try: uc.mem_write(d, uc.mem_read(s,n))
                except: pass
            do_return(clean, 0); return
        if kind == 'rd':
            esp = uc.reg_read(X.UC_X86_REG_ESP)
            buf = struct.unpack('<I', uc.mem_read(esp+4,4))[0]
            cnt = struct.unpack('<I', uc.mem_read(esp+8,4))[0]
            if fpos+cnt <= len(DISK): uc.mem_write(buf, DISK[fpos:fpos+cnt])
            fpos += cnt
            do_return(clean, cnt); return
        if kind == 'rd2':
            esp = uc.reg_read(X.UC_X86_REG_ESP)
            buf = struct.unpack('<I', uc.mem_read(esp+4,4))[0]
            cnt = struct.unpack('<I', uc.mem_read(esp+8,4))[0]
            if fpos+cnt <= len(DISK): uc.mem_write(buf, DISK[fpos:fpos+cnt])
            fpos += cnt
            do_return(clean, cnt); return
    if address == 0x47da10:   # object 1-byte reader -> trace (sequential file stream)
        global obj_count, obj_start
        if obj_start is None: obj_start = fpos
        off = obj_start + obj_count
        b = DISK[off] if off < len(DISK) else 0
        trace.append((cur_section, off, 1, b)); read_1byte += 1; obj_count += 1
        return

uc.hook_add(UC_HOOK_CODE, hook_code)
try:
    uc.emu_start(0x47f350, 0x47f4d0)   # pass 1 only (stop before pass-2 sub-loaders)
except UcError as e:
    print('UC ERROR at EIP=0x%x:' % uc.reg_read(X.UC_X86_REG_EIP), e)
except Exception as e:
    import traceback; traceback.print_exc()

print('total 1-byte object reads traced:', read_1byte)
print('fpos (raw consumed):', fpos)
from collections import OrderedDict
secs = OrderedDict()
for sec, off, sz, b in trace:
    d = secs.setdefault(sec, [None, None, 0])
    if d[0] is None: d[0] = off
    d[1] = off; d[2] += 1
print('\n%-8s %8s %8s %6s' % ('section','start','end','reads'))
for sec,(s,e,n) in secs.items():
    print('%-8s %8d %8d %6d' % (sec, s, e, n))
# save trace + section map
import json
with open('scripts/_sndata_trace.json','w') as f:
    json.dump({'obj_start':obj_start,'total':read_1byte,
               'sections':{k:{'start':v[0],'end':v[1],'reads':v[2]} for k,v in secs.items()},
               'trace':trace}, f)
print('saved scripts/_sndata_trace.json')
