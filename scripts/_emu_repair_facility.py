#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unicorn 闭合：修复(Repair) 效果 0x437910 中 0x4ebcd0(a,b) 语义 + 0x43e7d0 设施等级写入。

静态结论（续23）：
  - esi -> FACILITY_SLOTS @0x513a78[i*5]：byte[0]=type(0xff=空), byte[1]=level/战力值
  - 0x43e7a0 = (type!=0xff) ? byte[1] : 0
  - 0x43e7d0(inc) = byte[1] = min(byte[1]+inc, commander.byte[0xd])  via 0x4ebcf0
  - 0x4ebcd0(new_level, old_level) = max(0, new-old); test ax,ax -> 修复成功 iff 等级上升

本脚本 emu 叶函数 0x43e7a0 / 0x43e7d0 / 0x4ebcd0 及合成路径，不跑完整 0x437910 UI 链。
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

import struct, sys
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import (
    UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX)

BASE = 0x400000
IMG = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
STACK = 0x600000
SENTINEL = 0x610000
FACILITY = 0x513a78          # slot 0 in runtime buffer
CMDR = 0x513534              # commander object for 0x43cb50
BATTLE_TYPE = 0x513548       # 0x43ca10 reads this; must be non-zero for 0x43cb50 path

GET_LEVEL = 0x43e7a0
ADD_LEVEL = 0x43e7d0
SATSUB16 = 0x4ebcd0
CLAMP_ADD = 0x4ebcf0


def patch(mu, va, code):
    mu.mem_write(va, bytes(code))


def setup_mu():
    mu = Uc(UC_ARCH_X86, UC_MODE_32)
    mu.mem_map(BASE, 0x200000)
    mu.mem_write(BASE, IMG)
    mu.mem_map(STACK, 0x2000)
    mu.mem_map(SENTINEL, 0x1000)
    mu.mem_write(SENTINEL, b'\xc3')
    mu.mem_write(BATTLE_TYPE, bytes([1]))
    mu.mem_write(CMDR, bytes([0] * 0x20))
    mu.mem_write(0x513534, struct.pack('<I', CMDR))  # 0x43cb50 -> commander ptr
    mu.hook_add(UC_HOOK_CODE, lambda m, a, s, u: m.emu_stop() if a == SENTINEL else None)
    return mu


def emu_call(mu, func, ecx=None, stack_args=None, ret_width=8):
    sp = STACK + 0x800
    words = [SENTINEL]
    if stack_args:
        words.extend(stack_args)
    mu.mem_write(sp, struct.pack('<' + 'I' * len(words), *words))
    mu.reg_write(UC_X86_REG_ESP, sp)
    if ecx is not None:
        mu.reg_write(UC_X86_REG_ECX, ecx)
    mu.reg_write(UC_X86_REG_EIP, func)
    mu.emu_start(func, func + 0x100)
    eax = mu.reg_read(UC_X86_REG_EAX)
    return (eax & 0xFFFF) if ret_width == 16 else (eax & 0xFF)


def main():
    mu = setup_mu()

    ok = 0
    fail = 0

    def check(name, got, exp):
        nonlocal ok, fail
        if got == exp:
            ok += 1
            print('  PASS  %s = %s' % (name, got))
        else:
            fail += 1
            print('  FAIL  %s = %s (expected %s)' % (name, got, exp))

    print('=== 0x43e7a0 getFacilityLevel ===')
    mu.mem_write(FACILITY, bytes([2, 40, 0, 0, 1]))  # type=2, level=40
    check('active level', emu_call(mu, GET_LEVEL, ecx=FACILITY), 40)
    mu.mem_write(FACILITY, bytes([0xff, 99, 0, 0, 0]))
    check('empty slot', emu_call(mu, GET_LEVEL, ecx=FACILITY), 0)

    print('\n=== 0x4ebcf0 min(cur+v,cap) via 0x43e7d0 ===')
    cases = [
        (30, 10, 100, 40),
        (30, 10, 35, 35),
        (90, 20, 100, 100),
    ]
    for old, inc, cap, exp in cases:
        mu.mem_write(FACILITY, bytes([1, old, 5, 6, 1]))
        mu.mem_write(CMDR + 0x0d, bytes([cap]))
        emu_call(mu, ADD_LEVEL, ecx=FACILITY, stack_args=[inc])
        new = mu.mem_read(FACILITY + 1, 1)[0]
        check('old=%d inc=%d cap=%d -> %d' % (old, inc, cap, exp), new, exp)

    print('\n=== 0x4ebcd0 repair success gate (new, old) ===')
    for new, old, exp_nonzero in [(45, 40, True), (40, 40, False), (35, 40, False)]:
        delta = emu_call(mu, SATSUB16, stack_args=[new, old], ret_width=16)
        check('satsub16(%d,%d)>0=%s' % (new, old, exp_nonzero), (delta > 0), exp_nonzero)

    print('\n=== integrated repair path ===')
    mu.mem_write(FACILITY, bytes([3, 25, 2, 3, 1]))
    mu.mem_write(CMDR + 0x0d, bytes([80]))
    old = emu_call(mu, GET_LEVEL, ecx=FACILITY)
    inc = 15
    emu_call(mu, ADD_LEVEL, ecx=FACILITY, stack_args=[inc])
    new = emu_call(mu, GET_LEVEL, ecx=FACILITY)
    delta = emu_call(mu, SATSUB16, stack_args=[new, old], ret_width=16)
    check('integrated delta', delta, new - old)
    check('integrated success', delta > 0, True)

    print('\n%d PASS / %d FAIL' % (ok, fail))
    sys.exit(1 if fail else 0)


if __name__ == '__main__':
    main()
