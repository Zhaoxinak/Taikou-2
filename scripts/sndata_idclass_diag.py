#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnostic: find the faulting address for id=0."""
import struct
from unicorn import (
    Uc, UC_ARCH_X86, UC_MODE_32, UC_PROT_ALL,
    UC_HOOK_MEM_READ_UNMAPPED, UC_HOOK_CODE,
)
from unicorn.x86_const import (
    UC_X86_REG_EDX, UC_X86_REG_EAX, UC_X86_REG_ESP, UC_X86_REG_EIP,
)

BASE = 0x400000
IMG  = r"F:\Games\Taikou 2\scripts\_unpacked_mem.bin"
with open(IMG, "rb") as f:
    MEM = f.read()

REC_BUF = 0x600000
ENT_BUF = 0x600004
HEAP    = 0x630000
STACK   = 0xC00000

mu = Uc(UC_ARCH_X86, UC_MODE_32)
mu.mem_map(BASE, len(MEM), UC_PROT_ALL)
mu.mem_map(REC_BUF & 0xFFFF0000, 0x20000, UC_PROT_ALL)
mu.mem_map(HEAP, 0x10000, UC_PROT_ALL)
mu.mem_map(STACK, 0x10000, UC_PROT_ALL)
mu.mem_write(BASE, MEM)

mu.mem_write(0x49f6b0, b"\xb8" + struct.pack("<I", REC_BUF) + b"\xc3")
mu.mem_write(0x49f5e0, b"\xb8" + struct.pack("<I", ENT_BUF) + b"\xc3")
mu.mem_write(0x4787c0, b"\x5f\x5e\xc2\x14\x00")
mu.mem_write(0x4eefa0, b"\xc2\x04\x00")
mu.mem_write(0x47ae20, b"\xc3")
mu.mem_write(0x478a20, b"\xc3")
mu.mem_write(0x516638, b"\x00")
mu.mem_write(ENT_BUF + 0x2c, struct.pack("<H", 0x0700))

faults = []
def hook_unmapped(mu, access, address, size, value, data):
    faults.append((address, size))
    print(f"  UNMAPPED READ va=0x{address:x} size={size}")
    return False

last_pc = [0]
def hook_code(mu, address, size, data):
    last_pc[0] = address

mu.hook_add(UC_HOOK_MEM_READ_UNMAPPED, hook_unmapped)
mu.hook_add(UC_HOOK_CODE, hook_code)

mu.mem_write(REC_BUF, struct.pack("<H", 0))
esp = STACK + 0x8000
mu.reg_write(UC_X86_REG_ESP, esp)
try:
    mu.emu_start(0x462fd0, 0x4630b2, count=200000)
    print("completed without error")
except Exception as e:
    print(f"ERROR: {e}")
    print(f"  last PC before fault = 0x{last_pc[0]:x}")
print("faults seen:", faults[:10])
