# -*- coding: utf-8 -*-
"""Emulate 0x49fa40 (pay) natively; derive formula empirically."""
import os
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESP, UC_X86_REG_EIP

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
IMG = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
STACK = 0x7F000
CAS_TBL = 0x51eb88
CAS_STRIDE = 31
KOKU_TBL = 0x5179b8          # 国政治表 base (stride 14)
KOKU_STRIDE = 14
ENT_TBL = 0x519868
ENT_STRIDE = 47
FUNC = 0x49FA40


def run_pay(castle_idx, heibei, force_gate=True):
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(BASE, len(IMG))
    uc.mem_write(BASE, IMG)
    uc.mem_map(STACK - 0x10000, 0x20000)
    A = CAS_TBL + castle_idx * CAS_STRIDE
    # control A[0xc] = 兵員/規模 byte
    uc.mem_write(A + 0xc, bytes([heibei & 0xff]))
    if force_gate:
        # 国 = byte[castle+0]
        kuni = int.from_bytes(uc.mem_read(A, 1), "little")
        koku_ent = KOKU_TBL + kuni * KOKU_STRIDE
        ent_idx = int.from_bytes(uc.mem_read(koku_ent + 4, 2), "little")
        ent = ENT_TBL + ent_idx * ENT_STRIDE
        # set ent[+0x25] = castle_idx so 国主 stationed here
        uc.mem_write(ent + 0x25, bytes([castle_idx & 0xff]))
    esp = STACK
    uc.mem_write(esp + 4, A.to_bytes(4, "little"))
    uc.reg_write(UC_X86_REG_ESP, esp)
    uc.emu_start(FUNC, 0)
    return int.from_bytes(uc.mem_read(esp, 4), "little")  # caller's eax clobbered? read eax
    # Actually eax holds return; read via reg after stop. Re-do:


def run_pay2(castle_idx, heibei, force_gate=True):
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(BASE, len(IMG))
    uc.mem_write(BASE, IMG)
    uc.mem_map(STACK - 0x10000, 0x20000)
    A = CAS_TBL + castle_idx * CAS_STRIDE
    uc.mem_write(A + 0xc, bytes([heibei & 0xff]))
    if force_gate:
        kuni = int.from_bytes(uc.mem_read(A, 1), "little")
        koku_ent = KOKU_TBL + kuni * KOKU_STRIDE
        ent_idx = int.from_bytes(uc.mem_read(koku_ent + 4, 2), "little")
        ent = ENT_TBL + ent_idx * ENT_STRIDE
        uc.mem_write(ent + 0x25, bytes([castle_idx & 0xff]))
    RET = 0x90000
    uc.mem_map(RET, 0x1000)
    uc.mem_write(RET, b"\xc3")  # ret
    esp = STACK
    uc.mem_write(esp, RET.to_bytes(4, "little"))      # return address
    uc.mem_write(esp + 4, A.to_bytes(4, "little"))    # arg0
    uc.reg_write(UC_X86_REG_ESP, esp)
    uc.emu_start(FUNC, RET)
    return uc.reg_read(UC_X86_REG_EAX)


if __name__ == "__main__":
    print("castle heibei -> pay (gate forced)")
    for c in (0, 7, 30, 100):
        for h in (0, 1, 10, 50, 100, 167, 200, 255):
            try:
                p = run_pay2(c, h, True)
            except Exception as e:
                p = f"ERR:{e}"
            print(f"  c={c:3d} h={h:3d} -> {p}")
