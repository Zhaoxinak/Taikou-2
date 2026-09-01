#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unicorn 闭合 0x443d80 技能注册表构建器 + 10B 扫描流格式。

扫描流 @0x51e1f8：200 条 × stride 10B（esi 指向 record+8）。
  record+6 : word  NPC 类别键（与 (npc-0x517850)/12 派生键比较，ah|=0x80）
  record+8 : word  技能标志（bit7=1 且 (al&7)∈{0..6} 才写入注册表）
  record+0 : 8B   技能条目 payload；注册表存 &record+0

NPC 池 @0x517850 stride 12B；当前 NPC 指针 @0x52063c。
注册表基址指针 @0x517838 -> dword[] 条目指针。
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
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX

BASE = 0x400000
IMG = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
STACK = 0x600000
SENTINEL = 0x610000
POOL = 0x517850
NPC_CUR = 0x52063c
REG_PTR = 0x517838
STREAM = 0x51e1f8
REG_BUF = 0x720000

BUILDER = 0x443d80
SKILL_NAMES = {0: '马术', 1: '忍术', 2: '铁炮', 3: '筑城', 4: '兵法', 5: '剑术', 6: '口才'}


def npc_category_key(pool_index):
    return pool_index & 0xFF | 0x8000


def make_record(pool_index, skill_cat, extra=0):
    rec = bytearray(10)
    struct.pack_into('<H', rec, 6, npc_category_key(pool_index))
    struct.pack_into('<H', rec, 8, 0x80 | (skill_cat & 7) | ((extra & 0xF) << 3))
    rec[0] = 0xA0 + skill_cat
    rec[1] = pool_index
    return bytes(rec)


def main():
    mu = Uc(UC_ARCH_X86, UC_MODE_32)
    mu.mem_map(BASE, 0x200000)
    mu.mem_write(BASE, IMG)
    mu.mem_map(STACK, 0x2000)
    mu.mem_map(SENTINEL, 0x1000)
    mu.mem_map(REG_BUF, 0x10000)
    mu.mem_write(SENTINEL, b'\xc3')
    mu.mem_write(REG_PTR, struct.pack('<I', REG_BUF))

    pool_index = 3
    npc_ptr = POOL + pool_index * 12
    mu.mem_write(npc_ptr, bytes([0] * 12))
    mu.mem_write(NPC_CUR, struct.pack('<I', npc_ptr))

    # 3 records at stream slots 0,1,2; slot2 wrong pool index
    mu.mem_write(STREAM - 8 + 0 * 10, make_record(3, 1))
    mu.mem_write(STREAM - 8 + 1 * 10, make_record(3, 4))
    mu.mem_write(STREAM - 8 + 2 * 10, make_record(5, 2))
    for i in range(3, 200):
        mu.mem_write(STREAM - 8 + i * 10 + 6, struct.pack('<H', 0x9999))

    mu.hook_add(UC_HOOK_CODE, lambda m, a, s, u: m.emu_stop() if a == SENTINEL else None)
    sp = STACK + 0x800
    mu.mem_write(sp, struct.pack('<I', SENTINEL))
    mu.reg_write(UC_X86_REG_ESP, sp)
    mu.reg_write(UC_X86_REG_EIP, BUILDER)
    mu.emu_start(BUILDER, BUILDER + 0x100)

    count = mu.reg_read(UC_X86_REG_EAX) & 0xFFFF
    entries = []
    for i in range(count):
        p = struct.unpack('<I', mu.mem_read(REG_BUF + i * 4, 4))[0]
        if p:
            b0, b1 = mu.mem_read(p, 2)
            entries.append((p, b0, b1, SKILL_NAMES.get(b0 - 0xA0, '?')))

    print('builder count =', count)
    for p, b0, b1, nm in entries:
        print('  [%#x] pool=%d skill=%s' % (p, b1, nm))

    ok = count == 2 and len(entries) == 2 and entries[0][3] == '忍术' and entries[1][3] == '兵法'
    print('\n' + ('ALL PASS' if ok else 'FAIL'))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
