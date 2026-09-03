#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续227-下一步(B) 实证: 逐 id 跑 0x462fd0 捕获 (edx 类别键, ret class)。
桩: 0x49f6b0->record buf; 0x49f5e0->entity buf; 0x4787c0(find) no-op;
0x4eefa0(enqueue)/0x47ae20/0x478a20 no-op。
"""
import struct
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_PROT_ALL
from unicorn.x86_const import UC_X86_REG_EDX, UC_X86_REG_EAX, UC_X86_REG_ESP

BASE = 0x400000
IMG  = r"F:\Games\Taikou 2\scripts\_unpacked_mem.bin"
with open(IMG, "rb") as f:
    MEM = f.read()

REC_BUF = 0x600000
ENT_BUF = 0x600004
HEAP    = 0x630000
STACK   = 0xC00000

mu = Uc(UC_ARCH_X86, UC_MODE_32)
mu.mem_map(BASE, len(MEM), UC_PROT_ALL)       # code+data
mu.mem_map(REC_BUF & 0xFFFF0000, 0x20000, UC_PROT_ALL)   # 0x600000..0x620000
mu.mem_map(HEAP, 0x10000, UC_PROT_ALL)                    # 0x630000..0x640000
mu.mem_map(STACK, 0x10000, UC_PROT_ALL)                  # 0xC00000..
mu.mem_write(BASE, MEM)

# 桩: 0x49f6b0 -> mov eax,REC_BUF; ret ; 0x49f5e0 -> mov eax,ENT_BUF; ret
mu.mem_write(0x49f6b0, b"\xb8" + struct.pack("<I", REC_BUF) + b"\xc3")
mu.mem_write(0x49f5e0, b"\xb8" + struct.pack("<I", ENT_BUF) + b"\xc3")
# 0x4787c0 find -> pop edi; pop esi; ret 0x14
mu.mem_write(0x4787c0, b"\x5f\x5e\xc2\x14\x00")
# 0x4eefa0 enqueue -> ret 4
mu.mem_write(0x4eefa0, b"\xc2\x04\x00")
# 0x47ae20 / 0x478a20 -> ret
mu.mem_write(0x47ae20, b"\xc3")
mu.mem_write(0x478a20, b"\xc3")

# gating globals: class1 gate off (byte[0x516638]=0); entity.0x2c>>8&7 !=0 (include class2/5)
mu.mem_write(0x516638, b"\x00")
mu.mem_write(ENT_BUF + 0x2c, struct.pack("<H", 0x0700))

# hooks
captured_edx = []
captured_ret = []
hook_be00_on = False
def hook_be00(mu, address, size, data):
    global hook_be00_on
    if address == 0x47be00 and hook_be00_on:
        captured_edx.append(mu.reg_read(UC_X86_REG_EDX))
        hook_be00_on = False   # 只捕一次
def hook_ret(mu, address, size, data):
    if address == 0x4630b0:
        captured_ret.append(mu.reg_read(UC_X86_REG_EAX) & 0xffff)

from unicorn import UC_HOOK_CODE
mu.hook_add(UC_HOOK_CODE, hook_be00)
mu.hook_add(UC_HOOK_CODE, hook_ret)

def run_one(idw):
    global hook_be00_on
    captured_edx.clear(); captured_ret.clear()
    hook_be00_on = True
    mu.mem_write(REC_BUF, struct.pack("<H", idw & 0xffff))
    esp = STACK + 0x8000
    mu.reg_write(UC_X86_REG_ESP, esp)
    try:
        mu.emu_start(0x462fd0, 0x4630b2, count=200000)
    except Exception as e:
        return ("ERR", str(e)[:60])
    edx = captured_edx[0] if captured_edx else None
    ret = captured_ret[0] if captured_ret else None
    return (edx, ret)

print(f"{'id':>5} {'edx@be00':>10} {'ret@462fd0':>12}")
results = {}
for idw in range(0, 215):
    r = run_one(idw)
    edx, ret = r[0], r[1]
    tag = f"edx={edx}" + (f" ret={ret}" if ret is not None else "")
    if isinstance(r, tuple) and len(r)==2 and r[0] is None and r[1] is None:
        tag = "LOOP/no-edx"
    results[idw] = (edx, ret)
    print(f"{idw:>5} {str(edx):>10} {str(ret):>12}")

# 汇总: 每个 (edx, ret) 组合
from collections import Counter
combos = Counter((results[i][0], results[i][1]) for i in range(215))
print("\n(edx, ret) 组合数:", len(combos))
for k,v in sorted(combos.items(), key=lambda x:(x[0][0] is None, x[0][0] or 0)):
    print(f"  edx={k[0]} ret={k[1]}  x{v}")
