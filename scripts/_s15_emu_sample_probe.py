#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S15 段C runtime-var val emu 取样可行性探针（续217）。
钩 set_c(0x49c500) 抓 (idx,val)；先 sanity 直调 set_c，再尝试跑 owner 0x413d10（segC[0]×3 + segC[1]×1）。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_ECX, UC_X86_REG_EIP, UC_X86_REG_EAX
from emu_harness import Emu

BASE = 0x400000
SET_C = 0x49c500
BUF = 0x5203c0

captured = []

def make_harness():
    e = Emu()
    # IAT 兜底：整页 0x3000 ret（续209）
    try:
        e.mu.mem_map(0x3000, 0x1000)
        e.mu.mem_write(0x3000, b"\xc3" * 0x1000)  # ret
    except Exception:
        pass
    return e

def hook_setc(mu, address, size, ud):
    if address != SET_C:
        return
    esp = mu.reg_read(UC_X86_REG_ESP)
    idx = mu.mem_read(esp + 4, 4)
    val = mu.mem_read(esp + 8, 1)
    ecx = mu.reg_read(UC_X86_REG_ECX)
    idx = int.from_bytes(idx, 'little') & 0xff
    val = int.from_bytes(val, 'little')
    captured.append((hex(address), idx, val, hex(ecx)))

def main():
    e = make_harness()
    h = e.mu.hook_add(UC_HOOK_CODE, hook_setc)
    # sanity: 直调 set_c(2, 7)，ecx=BUF
    captured.clear()
    try:
        e.call(SET_C, [2, 7], regs={UC_X86_REG_ECX: BUF})
        print("sanity set_c(2,7) -> captured:", captured)
        print("  buf[0x13+2]=", e.mu.mem_read(BUF + 0x13 + 2, 1))
    except Exception as ex:
        print("sanity set_c crashed:", ex)

    # 尝试跑 owner 0x413d10（segC[0]×3 + segC[1]×1 via 0x413db0）
    captured.clear()
    try:
        r = e.call(0x413d10, [], regs={}, max_steps=0x200000)
        print("\nowner 0x413d10 ran OK. set_c writes captured:", captured)
        print("  eax=%#x ecx=%#x" % (r['eax'], r['ecx']))
    except Exception as ex:
        print("\nowner 0x413d10 crashed (concrete sampling needs booted interpreter):", repr(ex)[:200])
        print("  partial captured before crash:", captured)

    e.mu.hook_del(h)

if __name__ == '__main__':
    main()
