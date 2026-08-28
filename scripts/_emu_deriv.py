# -*- coding: utf-8 -*-
"""Emulate the 3 SECT_A (col,row) index-derivation helpers, per 续16 plan:
  0x43a410(x) = byte[x + 0x512f28]   (runtime buffer, memset 0xff at prep)
  0x43a420(x) = word[x*4 + 0x503710] (DIR8, static)
  0x43a440(x) = word[x*4 + 0x503712] (SPAWN_TYPE_TBL, static)
Confirms they are pure table lookups; shows 0x43a410 needs runtime fill.
"""
import struct, sys
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_EIP

BASE = 0x400000
IMG = open('scripts/_unpacked_mem.bin', 'rb').read()
assert len(IMG) == 0x200000

FUNCS = {'a410': 0x43a410, 'a420': 0x43a420, 'a440': 0x43a440}
STACK = 0x600000

def emu_call(va, x, buf_fill=None):
    mu = Uc(UC_ARCH_X86, UC_MODE_32)
    mu.mem_map(BASE, 0x200000)
    mu.mem_write(BASE, IMG)
    mu.mem_map(STACK, 0x2000)
    if buf_fill is not None:
        mu.mem_write(0x512f28, bytes([buf_fill]) * 0xb4)
    sp = STACK + 0x800
    retaddr = STACK + 0x900
    frame = struct.pack('<I', retaddr) + struct.pack('<I', x & 0xffff)
    mu.mem_write(sp, frame)
    mu.reg_write(UC_X86_REG_ESP, sp)
    mu.reg_write(UC_X86_REG_EIP, va)
    stop = [False]
    def hk(mu, address, size, data):
        if address == retaddr:
            stop[0] = True
            mu.emu_stop()
    mu.hook_add(UC_HOOK_CODE, hk)
    try:
        mu.emu_start(va, va + 0x200)
    except Exception as e:
        return ('EXC', str(e))
    if not stop[0]:
        return ('EXC', 'no-return')
    return mu.reg_read(UC_X86_REG_EAX) & 0xffff

def show(name, va, n=16, buf_fill=None):
    print('=== %s x=0..%d ===' % (name, n-1))
    for x in range(n):
        r = emu_call(va, x, buf_fill=buf_fill)
        if isinstance(r, tuple):
            print('  [%2d]=EXC:%s' % (x, r[1])); continue
        print('  [%2d]=%5d (0x%04x)' % (x, r, r))

show('0x43a420 (DIR8)', FUNCS['a420'])
show('0x43a440 (SPAWN_TYPE)', FUNCS['a440'])
show('0x43a410 (byte@0x512f28, static=0)', FUNCS['a410'])
show('0x43a410 (buf filled 0xAB)', FUNCS['a410'], buf_fill=0xAB)
print('\nCONFIRMED: 0x43a410 reads 0x512f28 (runtime buffer, memset 0xff at prep 0x43a080);')
print('0x43a420/0x43a440 are static table lookups (DIR8 / SPAWN_TYPE_TBL).')
