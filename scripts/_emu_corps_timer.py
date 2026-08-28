#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unicorn 闭合：corps 计略锁定计时数组 0x43daf0 / 0x43db20。

静态结论（续24）：
  - corps+0x19 起为 per-slot 16-bit 数组；index = 单位槽索引（0x43d980 在 corps+5 扫 5 槽）。
  - 0x43daf0(corps, index, delta) = word[idx] = min(cur+delta, 0xea60)  via 0x4ebca0
  - 0x43db20(corps, index, delta) = word[idx] = max(0, cur-delta)       via 0x4ebcd0
  - 牵制成功：0x437751 0x43daf0(0xfa=250)；失败次路径 0x43daf0(0x1f4=500)（GAME_DATA_SPEC）

本脚本只 emu 叶函数，不跑完整 0x437730 UI 链。
"""
import struct, sys
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_ECX, UC_X86_REG_EAX

BASE = 0x400000
IMG = open('scripts/_unpacked_mem.bin', 'rb').read()
STACK = 0x600000
SENTINEL = 0x610000
CORPS = 0x700000

ADD_TIMER = 0x43daf0
SUB_TIMER = 0x43db20
CAP = 0xea60


def setup_mu():
    mu = Uc(UC_ARCH_X86, UC_MODE_32)
    mu.mem_map(BASE, 0x200000)
    mu.mem_write(BASE, IMG)
    mu.mem_map(STACK, 0x2000)
    mu.mem_map(SENTINEL, 0x1000)
    mu.mem_map(CORPS, 0x1000)
    mu.mem_write(SENTINEL, b'\xc3')
    mu.mem_write(CORPS, bytes(0x80))
    mu.hook_add(UC_HOOK_CODE, lambda m, a, s, u: m.emu_stop() if a == SENTINEL else None)
    return mu


def word_at(mu, corps, index):
    off = 0x19 + index * 2
    return struct.unpack('<H', mu.mem_read(corps + off, 2))[0]


def emu_call(mu, func, ecx, index, delta):
    sp = STACK + 0x800
    mu.mem_write(sp, struct.pack('<III', SENTINEL, index, delta))
    mu.reg_write(UC_X86_REG_ESP, sp)
    mu.reg_write(UC_X86_REG_ECX, ecx)
    mu.reg_write(UC_X86_REG_EIP, func)
    mu.emu_start(func, func + 0x40)


def main():
    mu = setup_mu()
    ok = fail = 0

    def check(name, got, exp):
        nonlocal ok, fail
        if got == exp:
            ok += 1
            print('  PASS  %s = %s' % (name, got))
        else:
            fail += 1
            print('  FAIL  %s = %s (expected %s)' % (name, got, exp))

    print('=== 0x43daf0 add timer (pin success uses +250) ===')
    cases_add = [
        (0, 0, 250, 250),
        (1, 100, 250, 350),
        (2, CAP - 10, 250, CAP),
        (3, CAP, 250, CAP),
        (4, 500, 500, 1000),
    ]
    for idx, cur, delta, exp in cases_add:
        buf = bytearray(0x80)
        struct.pack_into('<H', buf, 0x19 + idx * 2, cur)
        mu.mem_write(CORPS, bytes(buf))
        emu_call(mu, ADD_TIMER, CORPS, idx, delta)
        check('idx=%d cur=%d +%d' % (idx, cur, delta), word_at(mu, CORPS, idx), exp)

    print('\n=== 0x43db20 subtract timer ===')
    mu.mem_write(CORPS, bytes(0x80))
    for idx, cur, delta, exp in [
        (0, 500, 200, 300),
        (1, 100, 150, 0),
        (2, 250, 250, 0),
    ]:
        buf = bytearray(0x80)
        struct.pack_into('<H', buf, 0x19 + idx * 2, cur)
        mu.mem_write(CORPS, bytes(buf))
        emu_call(mu, SUB_TIMER, CORPS, idx, delta)
        check('idx=%d cur=%d -%d' % (idx, cur, delta), word_at(mu, CORPS, idx), exp)

    print('\n=== integrated pin-style lock ===')
    buf = bytearray(0x80)
    mu.mem_write(CORPS, bytes(buf))
    slot = 2
    emu_call(mu, ADD_TIMER, CORPS, slot, 0xfa)
    check('after pin +0xfa', word_at(mu, CORPS, slot), 0xfa)
    emu_call(mu, ADD_TIMER, CORPS, slot, 0xfa)
    check('saturated second +0xfa', word_at(mu, CORPS, slot), 0x1f4)

    print('\n%d PASS / %d FAIL' % (ok, fail))
    sys.exit(1 if fail else 0)


if __name__ == '__main__':
    main()
