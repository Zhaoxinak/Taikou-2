# -*- coding: utf-8 -*-
"""
Unicorn 校准：牵制(Pin) 真实 mutator 0x437590。

公式（与火计/伏兵/挑衅同族 /100 contest，成功 = threshold >= contest）：
  threshold = ((rand40 + 80) * (byte[oppEnt+0xa] + 30*((byte[oppEnt+0x10]>>2)&3))) / 100
  contest   = rand50 + 20*(byte[corps1+8]&1) + 30*((byte[corps1+0x10]>>2)&3) + byte[corps1+0xa]
  if parity(0x43cab0): threshold += 20
"""
import struct, sys
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED
from unicorn.x86_const import (
    UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EDI, UC_X86_REG_ESI, UC_X86_REG_EAX, UC_X86_REG_EDX)

BASE = 0x400000
IMG = open('scripts/_unpacked_mem.bin', 'rb').read()
assert len(IMG) == 0x200000, len(IMG)

STACK = 0x600000
SENTINEL = 0x610000
CORPS1 = 0x700000   # 作用方 corps（contest）
CORPS2 = 0x701000   # 目标 corps（caller arg4，本公式未直读）
OPP_ENT = 0x702000  # 对方主将实体（threshold）
ENT1 = 0x703000
R40_ADDR = 0x7f001000
R50_ADDR = 0x7f002000
PARITY_ADDR = 0x7f003000
RAND_SEQ = 0x7f004000

FUNC = 0x437590
CAP = 0x437652


def patch(mu, va, code):
    mu.mem_write(va, bytes(code))


def div100(n):
    return ((n * 0x51EB851F) & 0xFFFFFFFFFFFFFFFF) >> 37


def predict(r40, r50, c1_stat, c1_tier, c1_flag8, c2_stat, c2_tier, parity):
    tier1 = (c1_tier >> 2) & 3
    tier2 = (c2_tier >> 2) & 3
    thr = div100((r40 + 80) * (c2_stat + 30 * tier2))
    con = r50 + 20 * (c1_flag8 & 1) + 30 * tier1 + c1_stat
    if parity:
        thr += 20
    return thr, con


def main():
    mu = Uc(UC_ARCH_X86, UC_MODE_32)
    mu.mem_map(BASE, 0x200000)
    mu.mem_write(BASE, IMG)
    mu.mem_map(STACK, 0x2000)
    mu.mem_map(SENTINEL, 0x1000)
    mu.mem_map(CORPS1, 0x1000)
    mu.mem_map(CORPS2, 0x1000)
    mu.mem_map(OPP_ENT, 0x1000)
    mu.mem_map(ENT1, 0x1000)
    mu.mem_map(R40_ADDR, 0x1000)
    mu.mem_map(R50_ADDR, 0x1000)
    mu.mem_map(PARITY_ADDR, 0x1000)
    mu.mem_map(RAND_SEQ, 0x1000)
    mu.mem_write(SENTINEL, b'\xc3')

    patch(mu, 0x4ebd60, b'\x31\xc0\xc3')  # 由 hook 覆写 eax
    patch(mu, 0x43cab0, b'\xa0' + struct.pack('<I', PARITY_ADDR) + b'\x83\xe0\x01\xc3')
    for stub in (0x43d630, 0x4997c0, 0x4352c0, 0x435320, 0x43d980, 0x43daf0,
                 0x43dbe0, 0x43dce0, 0x43e840, 0x43e7b0, 0x47ba40, 0x47b210,
                 0x499810, 0x499800, 0x49f190):
        patch(mu, stub, b'\xc3')

    captured = {}
    rand_calls = [0]

    def hook_code(mu, address, size, user_data):
        if address == 0x4ebd60:
            n = rand_calls[0]
            rand_calls[0] += 1
            val = struct.unpack('<I', mu.mem_read(R40_ADDR if n == 0 else R50_ADDR, 4))[0]
            mu.reg_write(UC_X86_REG_EAX, val & 0xffffffff)
            esp = mu.reg_read(UC_X86_REG_ESP)
            ret = struct.unpack('<I', mu.mem_read(esp, 4))[0]
            mu.reg_write(UC_X86_REG_ESP, esp + 4)
            mu.reg_write(UC_X86_REG_EIP, ret)
        elif address == CAP:
            captured['thr'] = mu.reg_read(UC_X86_REG_EDI) & 0xffff
            captured['con'] = mu.reg_read(UC_X86_REG_ESI) & 0xffff
            mu.emu_stop()

    mu.hook_add(UC_HOOK_CODE, hook_code)

    def hook_mem(mu, access, address, size, value, data):
        mu.mem_map(address & ~0xfff, 0x1000)
        return True

    mu.hook_add(UC_HOOK_MEM_UNMAPPED, hook_mem)

    def run(r40, r50, c1_stat, c1_tier_byte, c1_flag8, c2_stat, c2_tier_byte, parity):
        c1 = bytearray(0x40)
        c1[0x08] = c1_flag8 & 1
        c1[0x0a] = c1_stat & 0xff
        c1[0x10] = c1_tier_byte & 0xff
        opp = bytearray(0x40)
        opp[0x0a] = c2_stat & 0xff
        opp[0x10] = c2_tier_byte & 0xff
        mu.mem_write(CORPS1, bytes(c1))
        mu.mem_write(CORPS2, bytes(bytearray(0x40)))
        mu.mem_write(OPP_ENT, bytes(opp))
        mu.mem_write(ENT1, bytes(bytearray(0x40)))
        mu.mem_write(R40_ADDR, struct.pack('<I', r40))
        mu.mem_write(R50_ADDR, struct.pack('<I', r50))
        mu.mem_write(PARITY_ADDR, struct.pack('<B', parity & 1))
        rand_calls[0] = 0
        captured.clear()

        sp = STACK + 0x800
        args = [CORPS1, ENT1, OPP_ENT, CORPS2, CORPS1, 0, ENT1]
        frame = bytearray(4 + 4 * len(args))
        struct.pack_into('<I', frame, 0, SENTINEL)
        for i, a in enumerate(args):
            struct.pack_into('<I', frame, 4 + i * 4, a)
        mu.mem_write(sp, bytes(frame))
        mu.reg_write(UC_X86_REG_ESP, sp)
        mu.reg_write(UC_X86_REG_EIP, FUNC)
        try:
            mu.emu_start(FUNC, FUNC + 0x300)
        except Exception as e:
            print('  EXC', e, file=sys.stderr)
        thr_e = captured.get('thr', -1)
        con_e = captured.get('con', -1)
        thr_p, con_p = predict(r40, r50, c1_stat, c1_tier_byte, c1_flag8,
                               c2_stat, c2_tier_byte, parity)
        return thr_e, con_e, thr_p, con_p, thr_e == thr_p and con_e == con_p

    cases = [
        (10, 10, 150, 0x00, 0, 150, 0x00, 0),
        (10, 10, 150, 0x04, 0, 150, 0x00, 0),
        (30, 10, 150, 0x00, 0, 150, 0x00, 0),
        (10, 10, 150, 0x00, 1, 150, 0x00, 0),
        (10, 10, 150, 0x00, 0, 150, 0x08, 0),
        (10, 10, 150, 0x00, 0, 150, 0x00, 1),
    ]
    print('%-4s %-4s c1=%-3s c2=%-3s thr_e thr_p con_e con_p OK')
    print('-' * 60)
    passed = 0
    for c in cases:
        thr_e, con_e, thr_p, con_p, ok = run(*c)
        passed += ok
        print('%-4d %-4d %-5d %-5d %-5d %-5d %-5d %-5d %s' % (
            c[0], c[1], c[2], c[5], thr_e, thr_p, con_e, con_p, 'PASS' if ok else 'FAIL'))
    print('-' * 60)
    print('RESULT: %d/%d PASS' % (passed, len(cases)))
    thr, con = predict(10, 10, 150, 0, 0, 150, 0, 0)
    print('Sample r40=10,r50=10,stat=150 -> thr=%d con=%d -> %s' % (
        thr, con, 'SUCCESS(main)' if thr >= con else 'FAIL(main)'))


if __name__ == '__main__':
    main()
