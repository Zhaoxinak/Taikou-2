# -*- coding: utf-8 -*-
"""Find where the per-type handler pointer 0x4fb09c is assigned, and the
type-switch that selects it. Search the whole image for writes to 0x4fb09c
and for tables of function pointers near it."""
import os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
HERE = os.path.dirname(os.path.abspath(__file__))
IMG = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

def struct_pack(x):
    return x.to_bytes(4, 'little')

TARGET = 0x4fb09c

# 1) direct writes: mov [0x4fb09c], reg  /  mov dword ptr [0x4fb09c], imm/reg
print("===== writes to 0x4fb09c =====")
found = []
for va in range(BASE, BASE + len(IMG) - 8, 1):
    # pattern: C7 05 <4-byte LE addr>  (mov dword ptr [disp32], imm32)
    if IMG[va-BASE:va-BASE+6] == b'\xc7\x05' + struct_pack(TARGET):
        imm = int.from_bytes(IMG[va-BASE+6:va-BASE+10], 'little')
        found.append((va, 'mov [4fb09c], 0x%x' % imm))
    # pattern: 89 /r ;  mov [disp32], reg  ->  0x89 0x05 <addr> OR 0x89 modrm
    # handle: 89 05 <addr32>  (mov [disp32], eax) and 89 0d/15/1d/25/2d/35/3d
    if IMG[va-BASE] == 0x89 and IMG[va-BASE+1] in (0x05,0x0d,0x15,0x1d,0x25,0x2d,0x35,0x3d):
        addr = int.from_bytes(IMG[va-BASE+2:va-BASE+6], 'little')
        if addr == TARGET:
            regb = IMG[va-BASE+1]
            reg = {0x05:'eax',0x0d:'ecx',0x15:'edx',0x1d:'ebx',0x25:'esp',0x2d:'ebp',0x35:'esi',0x3d:'edi'}[regb]
            found.append((va, 'mov [4fb09c], %s' % reg))

# also mov reg, [4fb09c] reads (to know it's used)
for va in range(BASE, BASE + len(IMG) - 6, 1):
    if IMG[va-BASE:va-BASE+6] == b'\x8b\x0d' + struct_pack(TARGET):
        found.append((va, 'mov ecx, [4fb09c] (read)'))
    if IMG[va-BASE:va-BASE+6] == b'\x8b\x15' + struct_pack(TARGET):
        found.append((va, 'mov edx, [4fb09c] (read)'))
    if IMG[va-BASE:va-BASE+6] == b'\xa1' + struct_pack(TARGET):
        found.append((va, 'mov eax, [4fb09c] (read)'))

for (va, s) in sorted(found):
    print("  %s  %s" % (hex(va), s))

import struct
def struct_pack(x):
    return x.to_bytes(4, 'little')
