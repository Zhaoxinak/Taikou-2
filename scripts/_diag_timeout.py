#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断 3 个超时 owner（0x409250/0x40c350/0x40a4f0）为何跑满步数不触 set_c。
钩 UC_HOOK_CODE 统计 PC 频次找热循环体；打印 top PCs + 反汇编上下文。"""
import os, sys
from collections import Counter
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_ECX, UC_X86_REG_EBX, \
    UC_X86_REG_ESI, UC_X86_REG_EDI
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from emu_harness import Emu
from _disasm_all import load_image, disasm_all
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = load_image()
MD = Cs(CS_ARCH_X86, CS_MODE_32)
ENT_BASE = 0x519868
ENT_STRIDE = 0x47b
SET_C = 0x49c500
BUF = 0x5203c0


def make_emu():
    e = Emu()
    try:
        e.mu.mem_map(0x3000, 0x1000)
        e.mu.mem_write(0x3000, b"\xc3" * 0x1000)
    except Exception:
        pass
    return e


def diag(owner):
    e = make_emu()
    ent = ENT_BASE
    try:
        e.mu.mem_map(0, 0x1000)
        data = bytes(e.mu.mem_read(ent, ENT_STRIDE))
        e.mu.mem_write(0, data + b"\x00" * (0x1000 - ENT_STRIDE))
    except Exception:
        pass
    cnt = Counter()
    def hk(mu, ad, sz, ud):
        cnt[ad] += 1
        if ad == 0x4110e3:
            mu.reg_write(UC_X86_REG_EDI, ent)
        elif ad == 0x4110e8:
            mu.reg_write(UC_X86_REG_ESI, ent)
        elif ad == 0x413db7:
            mu.reg_write(UC_X86_REG_ESI, ent)
    hh = e.mu.hook_add(UC_HOOK_CODE, hk)
    try:
        e.call(owner, [0, 0, 0, 0, ent],
               regs={UC_X86_REG_ECX: BUF, UC_X86_REG_EBX: ent}, max_steps=0x80000)
        print(f"  owner {owner:#08x} 正常返回（未触步数上限）")
    except Exception as ex:
        print(f"  owner {owner:#08x} CRASHED: {ex}")
    e.mu.hook_del(hh)
    print(f"\n=== owner {owner:#08x} top PCs (hit set_c={cnt.get(SET_C,0)} 次) ===")
    for pc, c in cnt.most_common(12):
        print(f"  {pc:#08x}  x{c}")
    print("  --- disasm of top 6 PCs (±0x10) ---")
    for pc, _ in cnt.most_common(6):
        for ins in disasm_all(MD, MEM, 0x400000):
            if ins.address >= pc - 0x10 and ins.address < pc + 0x10:
                print(f"    {ins.address:#08x} {ins.mnemonic} {ins.op_str}")
            if ins.address >= pc + 0x10:
                break


for ow in (0x409250, 0x40c350, 0x40a4f0):
    diag(ow)
