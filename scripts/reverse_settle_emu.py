# -*- coding: utf-8 -*-
"""Emulate 0x4a61d0 (reverse 支給 castle→A) and observe the 3 transfers.

Batch-friendly: SettleEmu builds ONE Uc instance (maps the 2MB image once)
and re-runs many test cases cheaply by just rewriting A/C scratch + re-starting.
"""
import os
import sys
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESP, UC_X86_REG_EIP

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
IMG = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
STACK = 0x7F000
CAS_TBL = 0x51eb88
CAS_STRIDE = 31
KOKU_TBL = 0x5179b8
KOKU_STRIDE = 14
ENT_TBL = 0x519868
ENT_STRIDE = 47
FUNC = 0x4A61D0
RET = 0x90000
KUNI = 5
CIDX = 7


class SettleEmu:
    def __init__(self):
        self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        self.uc.mem_map(BASE, len(IMG))
        self.uc.mem_write(BASE, IMG)
        self.uc.mem_map(STACK - 0x10000, 0x20000)
        self.uc.mem_map(RET, 0x1000)
        self.uc.mem_write(RET, b"\xc3")

        def h(uc, addr, size, ud):
            esp = uc.reg_read(UC_X86_REG_ESP)
            ret = int.from_bytes(uc.mem_read(esp, 4), "little")
            uc.reg_write(UC_X86_REG_EAX, 1)   # 放行
            uc.reg_write(UC_X86_REG_ESP, esp + 4)
            uc.reg_write(UC_X86_REG_EIP, ret)
        self.uc.hook_add(UC_HOOK_CODE, h, begin=0x49AC90, end=0x49AC90)
        self.uc.hook_add(UC_HOOK_CODE, h, begin=0x4A5C40, end=0x4A5C40)

        # static setup (constant across runs): ent0[0x25]=CIDX, koku[国].word[+4]=0
        ent0 = ENT_TBL
        self.uc.mem_write(ent0 + 0x25, bytes([CIDX & 0xff]))
        koku = KOKU_TBL + KUNI * KOKU_STRIDE
        self.uc.mem_write(koku + 4, (0).to_bytes(2, "little"))

        # A record at scratch
        self.A = 0xB0000
        self.uc.mem_map(self.A, 0x1000)
        # C = real castle slot CIDX (overwritten each run)
        self.C = CAS_TBL + CIDX * CAS_STRIDE

    def run(self, a10, a12, a14, c10, c12, c14, a_heibei=50, c_heibei=50):
        uc = self.uc
        A, C = self.A, self.C
        uc.mem_write(A, bytes([KUNI & 0xff]))            # A[0] = 国
        for off, v in ((0x10, a10), (0x12, a12), (0x14, a14)):
            uc.mem_write(A + off, (v & 0xFFFF).to_bytes(2, "little"))
        uc.mem_write(A + 0xc, bytes([a_heibei & 0xff]))   # 兵員
        uc.mem_write(A + 0x1b, b"\x00")                   # gate off

        uc.mem_write(C, bytes([KUNI & 0xff]))             # castle[0] = 国
        for off, v in ((0x10, c10), (0x12, c12), (0x14, c14)):
            uc.mem_write(C + off, (v & 0xFFFF).to_bytes(2, "little"))
        uc.mem_write(C + 0xc, bytes([c_heibei & 0xff]))    # 兵員
        uc.mem_write(C + 0x1b, b"\x00")                   # gate off

        esp = STACK
        uc.mem_write(esp, RET.to_bytes(4, "little"))
        uc.mem_write(esp + 4, A.to_bytes(4, "little"))
        uc.reg_write(UC_X86_REG_ESP, esp)
        uc.emu_start(FUNC, RET)

        def rd(base, off):
            return int.from_bytes(uc.mem_read(base + off, 2), "little")
        return (rd(A, 0x10), rd(A, 0x12), rd(A, 0x14),
                rd(C, 0x10), rd(C, 0x12), rd(C, 0x14))


# standalone convenience (backward compatible)
_def = SettleEmu()
def emu(a10, a12, a14, c10, c12, c14, a_heibei=50, c_heibei=50):
    return _def.run(a10, a12, a14, c10, c12, c14, a_heibei, c_heibei)


if __name__ == "__main__":
    print("a10 a12 a14 | c10 c12 c14 -> A'(r10,r12,r14) C'(r10,r12,r14)")
    cases = [
        (1000, 100, 1000, 5000, 5000, 5000),
        (2000, 200, 2000, 8000, 10000, 8000),
        (500, 50, 500, 3000, 20000, 3000),
        (3000, 300, 3000, 2000, 15000, 2000),
        (100, 10, 100, 90000, 20000, 90000),
    ]
    for c in cases:
        out = emu(*c)
        print(f"  {c[0]:5d} {c[1]:4d} {c[2]:5d} | {c[3]:5d} {c[4]:5d} {c[5]:5d} -> "
              f"A'({out[0]:5d},{out[1]:4d},{out[2]:5d}) C'({out[3]:5d},{out[4]:5d},{out[5]:5d})")
