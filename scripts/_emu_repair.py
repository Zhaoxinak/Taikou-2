# -*- coding: utf-8 -*-
"""
Unicorn 校准：跑真实二进制 修复(Repair) 效果子程 0x437ad0，
抓 roll (落点 0x437b63 处的 cx)，验证其整数公式，重点复核
续13 "仍未知"：roll 是否含 value/5 项（value=byte[源corps+0x24]）。

受控输入：
  - esi (源 corps) 经 hook 0x437ad6 强制 = CORPS_ADDR，byte[CORPS+0x24]=value
  - 0x43d970(源corps) 桩 -> S_ADDR，byte[S+0xa]=commander_stat
  - 0x43d630(源corps) 桩 -> T_ADDR（修复成功分支外无关）
  - 0x4ebd60(rand%n) 桩 -> 固定 R
  - 0x43dba0 / 0x47ba40 / 0x47b210 / 0x4997c0 / 0x499810 / 0x499800 / 0x42b1b0 /
    0x49f190 / 0x439150 全桩安全化
  - CORPS[0x2c]&1 = 0 -> je 0x437b21 跳过 msg 块，直达 roll 计算

多组 (R, value, commander) -> 抓 cx=roll，拟合 roll = R + k*value + commander，
判定 k≈0.2(/5) / 0.1(/10) / 0(误植)。
"""
import struct, sys
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED, UC_MEM_FETCH_UNMAPPED
from unicorn.x86_const import (
    UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EDX, UC_X86_REG_EAX, UC_X86_REG_ECX,
    UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBX)

BASE = 0x400000
IMG = open('scripts/_unpacked_mem.bin', 'rb').read()
assert len(IMG) == 0x200000, len(IMG)

STACK = 0x600000
SENTINEL = 0x610000
T_ADDR = 0x700000
S_ADDR = 0x702000
CORPS_ADDR = 0x704000
R_ADDR = 0x7f001000      # 受控 rand%n 返回值（数据内存，避免反复 patch 代码触发块缓存）

FUNC = 0x437ad0
CAP = 0x437b63           # cmp cx,0x78  (cx = roll)

def patch(mu, va, code):
    mu.mem_write(va, bytes(code))

def main():
    mu = Uc(UC_ARCH_X86, UC_MODE_32)
    mu.mem_map(BASE, 0x200000)
    mu.mem_write(BASE, IMG)
    mu.mem_map(STACK, 0x2000)
    mu.mem_map(SENTINEL, 0x1000)
    mu.mem_map(T_ADDR, 0x1000)
    mu.mem_map(S_ADDR, 0x1000)
    mu.mem_map(CORPS_ADDR, 0x1000)
    mu.mem_map(R_ADDR, 0x1000)
    mu.mem_write(R_ADDR, struct.pack('<I', 10))
    mu.mem_write(SENTINEL, b'\xc3')

    # --- 安全桩 ---
    patch(mu, 0x4ebd60, b'\xa1' + struct.pack('<I', R_ADDR) + b'\xc3')   # rand%n -> [R_ADDR] (数据内存)
    patch(mu, 0x43d630, b'\xb8' + struct.pack('<I', T_ADDR) + b'\xc3')  # 目标实体 -> T
    patch(mu, 0x43d970, b'\xb8' + struct.pack('<I', S_ADDR) + b'\xc3')  # 源实体 -> S
    patch(mu, 0x43dba0, b'\xc3')                       # addField25 -> ret
    patch(mu, 0x4997c0, b'\xc3')                       # 置标志 -> ret
    patch(mu, 0x47ba40, b'\xc3')                       # msg(arg) -> ret
    patch(mu, 0x47b210, b'\xc3')                       # msg -> ret
    patch(mu, 0x42b1b0, b'\xc3')                       # -> ret
    patch(mu, 0x499810, b'\x33\xc0\xc3')               # -> 0
    patch(mu, 0x499800, b'\xc3')                       # -> ret
    patch(mu, 0x49f190, b'\x33\xc0\xc3')               # -> 0
    patch(mu, 0x439150, b'\xc3')                       # section A write -> ret

    captured = [0]

    def hook_code(mu, address, size, data):
        if address == 0x437ad6:
            # 强制 esi = 受控 corps，覆盖 0x437ad2 的 [esp+0xc] 读取
            mu.reg_write(UC_X86_REG_ESI, CORPS_ADDR)
        elif address == CAP:
            captured[0] = mu.reg_read(UC_X86_REG_ECX) & 0xffff
            mu.emu_stop()
            return
        elif address == SENTINEL:
            mu.emu_stop()

    mu.hook_add(UC_HOOK_CODE, hook_code)

    def hook_mem(mu, access, address, size, value, data):
        if access == UC_MEM_FETCH_UNMAPPED:
            mu.mem_map(address & ~0xfff, 0x1000)
            return True
        mu.mem_map(address & ~0xfff, 0x1000)
        return True
    mu.hook_add(UC_HOOK_MEM_UNMAPPED, hook_mem)

    def run(R, value, commander):
        # 更新 rand%n 受控返回值（走数据内存，不改代码）
        mu.mem_write(R_ADDR, struct.pack('<I', R & 0xffffffff))
        # 受控 corps：byte[0x24]=value, byte[0x2c]&1=0 (跳过 msg 块)
        corps = bytearray(64)
        corps[0x24] = value & 0xff
        corps[0x2c] = 0
        mu.mem_write(CORPS_ADDR, bytes(corps))
        # 受控源 entity：byte[0xa]=commander_stat
        s = bytearray(64)
        s[0x0a] = commander & 0xff
        mu.mem_write(S_ADDR, bytes(s))
        # 目标 entity（无关，但 0x43d630 返回 T 需可读）
        mu.mem_write(T_ADDR, bytes(64))

        captured[0] = -1
        sp = STACK + 0x800
        frame = bytearray(0x40)
        struct.pack_into('<I', frame, 0x00, SENTINEL)   # ret
        # [esp+0xc] 由 hook 覆盖，这里占位
        mu.mem_write(sp, bytes(frame))
        mu.reg_write(UC_X86_REG_ESP, sp)
        mu.reg_write(UC_X86_REG_EIP, FUNC)
        try:
            mu.emu_start(FUNC, FUNC + 0x400)
        except Exception as e:
            print('  [EXC %s]' % e, file=sys.stderr)
        return captured[0]

    print('%-6s %-8s %-10s %-10s %-12s %-12s %-12s' % ('R', 'value', 'cmd', 'roll', 'dRoll/dVal', 'guess/5', 'guess/10'))
    print('-' * 78)
    # 固定 R, commander，扫 value，看 roll 随 value 的斜率
    R, CMD = 10, 150
    rows = []
    for v in [0, 5, 10, 25, 50, 100]:
        roll = run(R, v, CMD)
        rows.append((R, v, CMD, roll))
        g5 = R + v // 5 + CMD
        g10 = R + v // 10 + CMD
        print('%-6d %-8d %-10d %-10s %-12s %-12d %-12d' % (R, v, CMD, roll, '-', g5, g10))
    print('-' * 78)
    # 用首末两点估斜率
    r0 = rows[0][3]; r1 = rows[-1][3]
    v0 = rows[0][1]; v1 = rows[-1][1]
    if r0 >= 0 and r1 >= 0:
        slope = (r1 - r0) / (v1 - v0)
        print('slope dRoll/dVal ~= %.4f  (0.2=/5, 0.1=/10, 0=误植)' % slope)
    # 控制：变 R 与 commander 确认线性
    print('-' * 78)
    print('control: vary R & commander (value=0)')
    for (Rc, Vc, Cc) in [(10,0,150),(30,0,150),(10,0,200),(30,0,200)]:
        roll = run(Rc, Vc, Cc)
        print('  R=%d val=%d cmd=%d -> roll=%s  (expect R+val+k*0+cmd)' % (Rc, Vc, Cc, roll))

if __name__ == '__main__':
    main()
