#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unicorn 闭合：0x51e1f0 物品/技能对象池（200×10B）模型。

续25 结论：
  - 池基址 0x51e1f0，stride 10，count 200；扫描指针常取 +8 (=0x51e1f8)
  - 初始化 0x47a390：每槽 dword[+0] = vtable 0x4fc0e0
  - 辅池 0x517728：20×12B，vtable 0x4fc0f0
  - 字段：+0 vptr / +4 word / +5 level / +6 owner_key / +8 flags
  - owner_key：玩家 ID (0x49f5d0→0x516624) 或 (npc_pool_index|0x8000)
  - flags：bit7=owned；bits0-2=category(0..7)；bits3-6=sub
  - 类别名 @0x507ea8：酒/书籍/道具/财宝/武器/南蛮物/美术品/茶具
  - getValue (vtable[0]=0x49c070) 按 category 计价

本脚本：init 池 + getValue 公式 + owner_key 匹配重建 + 续27 free-by-owner。

续27：EXE 无 first-fit 空槽工厂；生命周期 = 预置/转让 + 释放。
  - 0x4a3960(owner)：扫 +6，匹配则写 FFFF（实体移除时批量释放）
  - 0x4a4115：owner 批量重映射（实体索引变更）
"""
import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import (
    UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_ECX, UC_X86_REG_EAX)

BASE = 0x400000
IMG = open('scripts/_unpacked_mem.bin', 'rb').read()
STACK = 0x600000
SENTINEL = 0x610000

POOL = 0x51e1f0
VTBL = 0x4fc0e0
INIT = 0x47a390
GET_VALUE = 0x49c070
SET_FLAGS = 0x49bfc0
SET_OWNED = 0x49bff0
GET_OWNER = 0x49f5d0
FREE_BY_OWNER = 0x4a3960
PLAYER_ID = 0x516624

CAT_NAMES = ['酒', '书籍', '道具', '财宝', '武器', '南蛮物', '美术品', '茶具']


def predict_value(cat, level, sub):
    """Mirror 0x49c070 branches (floor then ceil clamp)."""
    if cat == 0:
        v = min(level, 0xfa)
        return max(v, 1)
    if cat == 1:
        v = (level + sub * 10) * 10
        v = min(v, 0x1964)
        return max(v, 0xa)
    if cat == 2:
        v = level * 20
        v = min(v, 0x1388)
        return max(v, 0x14)
    if cat == 3:
        v = (level + sub * 50) * 10
        v = min(v, 0x7ef4)
        return max(v, 0x64)
    if cat == 4:
        adj = (sub - 5) if sub > 5 else 0
        v = (level + adj * 5) * 200
        v = min(v, 0xea60)
        return max(v, 0xc8) if False else (v if v >= 0xc8 else 0xc8)  # see below
    # cat 5/6/7: (level * (sub+5)) << 2, clamp [0xc8, 0xc350]
    v = (level * (sub + 5)) << 2
    v = min(v, 0xc350)
    return max(v, 0xc8)


def predict_value_cat4(level, sub):
    adj = (sub - 5) if sub > 5 else 0
    v = (level + adj * 5) * 200  # (lvl+adj*5)*5*5*8? from asm:
    # lea eax,[eax+eax*4] (=*5); add ecx; lea eax,[ecx+ecx*4] (=*5); lea eax,[eax+eax*4] (=*5); shl 3 (=*8)
    # = (lvl + adj*5) * 5 * 5 * 8 = (lvl+adj*5)*200  YES
    v = min(v, 0xea60)
    # floor at 0xc8 from 0x49c1bc area shared
    return max(v, 0xc8)


def setup():
    mu = Uc(UC_ARCH_X86, UC_MODE_32)
    mu.mem_map(BASE, 0x200000)
    mu.mem_write(BASE, IMG)
    mu.mem_map(STACK, 0x2000)
    mu.mem_map(SENTINEL, 0x1000)
    mu.mem_write(SENTINEL, b'\xc3')
    mu.hook_add(UC_HOOK_CODE, lambda m, a, s, u: m.emu_stop() if a == SENTINEL else None)
    return mu


def call0(mu, func, ecx=None):
    sp = STACK + 0x800
    mu.mem_write(sp, struct.pack('<I', SENTINEL))
    mu.reg_write(UC_X86_REG_ESP, sp)
    if ecx is not None:
        mu.reg_write(UC_X86_REG_ECX, ecx)
    mu.reg_write(UC_X86_REG_EIP, func)
    mu.emu_start(func, func + 0x200)
    return mu.reg_read(UC_X86_REG_EAX)


def call1(mu, func, ecx, arg):
    sp = STACK + 0x800
    mu.mem_write(sp, struct.pack('<II', SENTINEL, arg))
    mu.reg_write(UC_X86_REG_ESP, sp)
    mu.reg_write(UC_X86_REG_ECX, ecx)
    mu.reg_write(UC_X86_REG_EIP, func)
    mu.emu_start(func, func + 0x40)
    return mu.reg_read(UC_X86_REG_EAX)


def make_obj(mu, slot, level, cat, sub, owner, owned=True):
    addr = POOL + slot * 10
    flags = (cat & 7) | ((sub & 0xf) << 3)
    if owned:
        flags |= 0x80
    buf = bytearray(10)
    struct.pack_into('<I', buf, 0, VTBL)
    buf[5] = level & 0xff
    struct.pack_into('<H', buf, 6, owner & 0xffff)
    struct.pack_into('<H', buf, 8, flags)
    mu.mem_write(addr, bytes(buf))
    return addr


def main():
    mu = setup()
    ok = fail = 0

    def check(name, got, exp):
        nonlocal ok, fail
        if got == exp:
            ok += 1
            print('  PASS  %s = %s' % (name, got))
        else:
            fail += 1
            print('  FAIL  %s = %s (expected %s)' % (name, got, exp))

    print('=== 0x47a390 init vtable stamp ===')
    mu.mem_write(POOL, bytes(2000))
    call0(mu, INIT)
    for slot in (0, 1, 99, 199):
        v = struct.unpack('<I', mu.mem_read(POOL + slot * 10, 4))[0]
        check('slot%d vtbl' % slot, v, VTBL)

    print('\n=== 0x49f5d0 owner key (player id) ===')
    mu.mem_write(PLAYER_ID, struct.pack('<H', 0x42))
    check('player_id', call0(mu, GET_OWNER) & 0xffff, 0x42)

    print('\n=== 0x49bff0 / 0x49bfc0 flags ===')
    addr = make_obj(mu, 0, 10, 2, 0, 0x42, owned=False)
    call1(mu, SET_OWNED, addr, 1)
    fl = struct.unpack('<H', mu.mem_read(addr + 8, 2))[0]
    check('set owned bit7', fl & 0x80, 0x80)
    call1(mu, SET_FLAGS, addr, 0x84)  # owned + cat4
    fl = struct.unpack('<H', mu.mem_read(addr + 8, 2))[0]
    check('set flags word', fl, 0x84)

    print('\n=== 0x49c070 getValue by category ===')
    cases = [
        # cat, level, sub, expected
        (0, 50, 0, 50),
        (0, 0, 0, 1),
        (0, 200, 0, 200),
        (1, 10, 2, (10 + 2 * 10) * 10),  # 300
        (2, 10, 0, 200),
        (2, 0, 0, 20),
        (3, 5, 1, (5 + 50) * 10),  # 550
        (4, 10, 3, max(10 * 200, 0xc8)),  # adj=0 -> 2000
        (4, 10, 7, max((10 + 2 * 5) * 200, 0xc8)),  # 4000
        (5, 10, 0, max((10 * 5) << 2, 0xc8)),  # 200
        (6, 20, 3, max((20 * 8) << 2, 0xc8)),  # 640
        (7, 1, 0, max((1 * 5) << 2, 0xc8)),  # floor 200
    ]
    for cat, lvl, sub, exp in cases:
        # re-derive cat4/5 carefully
        if cat == 4:
            exp = predict_value_cat4(lvl, sub)
        elif cat >= 5:
            exp = predict_value(cat, lvl, sub)
        elif cat == 1:
            exp = predict_value(1, lvl, sub)
        elif cat == 3:
            # (lvl + sub*50)*10
            v = (lvl + sub * 50) * 10
            exp = max(min(v, 0x7ef4), 0x64)
        addr = make_obj(mu, cat, lvl, cat, sub, 0x42, owned=True)
        got = call0(mu, GET_VALUE, ecx=addr) & 0xffff
        check('cat%d lvl=%d sub=%d (%s)' % (cat, lvl, sub, CAT_NAMES[cat]), got, exp)

    print('\n=== 0x4a3960 free-by-owner ===')
    call0(mu, INIT)
    make_obj(mu, 0, 1, 0, 0, 0x8012, owned=True)
    make_obj(mu, 1, 2, 1, 0, 0x8044, owned=True)
    make_obj(mu, 2, 3, 2, 0, 0x8012, owned=True)
    make_obj(mu, 3, 5, 3, 0, 0x42, owned=True)
    # cdecl free_by_owner(owner)
    sp = STACK + 0x800
    mu.mem_write(sp, struct.pack('<II', SENTINEL, 0x8012))
    mu.reg_write(UC_X86_REG_ESP, sp)
    mu.reg_write(UC_X86_REG_EIP, FREE_BY_OWNER)
    mu.emu_start(FREE_BY_OWNER, FREE_BY_OWNER + 0x40)
    o0 = struct.unpack('<H', mu.mem_read(POOL + 0 * 10 + 6, 2))[0]
    o1 = struct.unpack('<H', mu.mem_read(POOL + 1 * 10 + 6, 2))[0]
    o2 = struct.unpack('<H', mu.mem_read(POOL + 2 * 10 + 6, 2))[0]
    o3 = struct.unpack('<H', mu.mem_read(POOL + 3 * 10 + 6, 2))[0]
    check('slot0 freed', o0, 0xffff)
    check('slot1 kept', o1, 0x8044)
    check('slot2 freed', o2, 0xffff)
    check('slot3 kept', o3, 0x42)

    print('\n%d PASS / %d FAIL' % (ok, fail))
    sys.exit(1 if fail else 0)


if __name__ == '__main__':
    main()
