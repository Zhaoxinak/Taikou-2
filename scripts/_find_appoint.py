# -*- coding: utf-8 -*-
"""
穷举扫描：定位「大名(7)/城主(8) 任命·继承」路径的入口。

两条硬线索（不猜表形状，纯穷举）：
  1) set_rank(0x49a7e0) 的**所有调用点** —— 任命必然要写 word[+0x2c] 的 bit8..10
  2) 城表 0x51eb88 (stride 31) 的城主字段 +0x0a 附近绝对地址引用
  3) 直接写 rank 立即数 7 / 8 的位置（跳过 set_rank 的裸写）

映像：_unpacked_mem.bin 平坦映射，off = va - 0x400000。
"""
import sys, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM, X86_OP_MEM

BASE = 0x400000
IMG = open('scripts/_unpacked_mem.bin', 'rb').read()
assert len(IMG) == 0x200000, len(IMG)

SET_RANK = 0x49a7e0
CITY_TBL = 0x51eb88          # 城表 stride 31
CITY_LORD_OFF = 0x0a         # 城主武将编号

cs = Cs(CS_ARCH_X86, CS_MODE_32)
cs.detail = True

# ---- 1) 全镜像线性反汇编，收集 call 目标 + 地址引用 ----
calls_to_setrank = []
city_refs = []
imm78 = []          # 立即数 7 / 8 与 rank 相关的可疑点（仅当附近有 +0x2c/0x2d 时记录）

# 线性反汇编：按 4KB 块起步，遇无效指令 va+=1 重同步
va = BASE
end = BASE + len(IMG)
while va < end:
    off = va - BASE
    chunk = IMG[off:off + 0x1000]
    if not chunk:
        break
    count = 0
    for ins in cs.disasm(chunk, va):
        count += 1
        s = ins.op_str
        if ins.mnemonic == 'call':
            # call rel32 / call [..]
            for op in ins.operands:
                if op.type == X86_OP_IMM:
                    tgt = op.imm
                    if tgt == SET_RANK:
                        calls_to_setrank.append(ins.address)
        # 城表绝对地址引用
        if '%x' % CITY_TBL in s or ('0x%x' % CITY_TBL) in s:
            city_refs.append((ins.address, ins.mnemonic, s))
        for m in re.finditer(r'0x51e[bc][0-9a-f]{2,3}', s):
            a = int(m.group(0), 16)
            d = a - CITY_TBL
            if 0 <= d < 0x400:
                city_refs.append((ins.address, ins.mnemonic, s))
    va += 0x1000 if count else 1

print('=' * 70)
print('[1] call 0x49a7e0 (set_rank) 调用点: %d 处' % len(calls_to_setrank))
for a in calls_to_setrank:
    print('    0x%X' % a)

print()
print('=' * 70)
print('[2] 城表 0x51eb88 (+0..0x3ff) 绝对地址引用: %d 处' % len(city_refs))
seen = set()
for a, mn, s in city_refs:
    if (a, s) in seen:
        continue
    seen.add((a, s))
    print('    0x%X  %-8s %s' % (a, mn, s))

# ---- 3) 反汇编 set_rank 调用者所在函数，看 push 的参数 ----
print()
print('=' * 70)
print('[3] set_rank 调用点上下文（回溯 12 条指令找 push 立即数参数）')
for a in calls_to_setrank:
    off = a - BASE
    # 回溯 64 字节反汇编
    start = max(BASE, a - 0x40)
    d = IMG[start - BASE:off]
    ins_list = []
    for ins in cs.disasm(d, start):
        ins_list.append(ins)
    # 取最后 14 条
    tail = ins_list[-14:]
    print('  --- call @ 0x%X ---' % a)
    for ins in tail:
        mark = '   <<< CALL set_rank' if ins.address == a else ''
        print('       0x%X  %-8s %s%s' % (ins.address, ins.mnemonic, ins.op_str, mark))
