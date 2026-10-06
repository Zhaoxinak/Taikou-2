# -*- coding: utf-8 -*-
"""probe_nib_xref.py — 实体状态字低4位(getter 0x49a610 / setter 0x49a6b0) 全镜像交叉引用
目的: 钉死「登场可用槽」由谁置位 —— 若是死亡/除籍 handler, 则原生登场=空缺递补制。
"""
import sys, capstone
from capstone.x86 import X86_OP_IMM
sys.stdout.reconfigure(encoding='utf-8')
D = open(r'F:\Games\Taikou 2\Taikou2 Original\.rev\clean_dump.bin', 'rb').read()
BASE = 0x400000
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = True

TARGETS = {0x49a610: 'nib_get', 0x49a6b0: 'nib_set', 0x4a4d10: 'appear_routine',
           0x4a4fc0: 'genpuku_init', 0x47f7b0: 'instantiate', 0x49a860: 'set_bit15'}
TEXT = (0x401000, 0x4C4000)


def sweep(buf, va):
    i, n = 0, len(buf)
    while i < n:
        adv = False
        for size in range(1, 16):
            if i + size > n:
                break
            for ins in md.disasm(buf[i:i + size], va + i):
                if len(ins.bytes) == size:
                    yield ins
                    i += size
                    adv = True
                    break
            if adv:
                break
        if not adv:
            i += 1


buf = D[TEXT[0] - BASE: TEXT[1] - BASE]
print('扫描 .text 0x%X..0X%X (%d 字节)' % (TEXT[0], TEXT[1], len(buf)))
callers = {v: [] for v in TARGETS.values()}
# 快路径: E8 rel32 (call) / EB rel8 / 0F 8x rel32 (jcc) / 68 imm32 (push) / FF 25|15 [imm32]
import struct
i = 0
n = len(buf)
while i < n - 6:
    b = buf[i]
    va = TEXT[0] + i
    if b == 0xE8:
        rel = struct.unpack_from('<i', buf, i + 1)[0]
        t = (va + 5 + rel) & 0xFFFFFFFF
        if t in TARGETS:
            callers[TARGETS[t]].append((va, 'call 0x%X' % t))
        i += 5
        continue
    if b == 0x68:
        t = struct.unpack_from('<I', buf, i + 1)[0]
        if t in TARGETS:
            callers[TARGETS[t]].append((va, 'push 0x%X' % t))
        i += 5
        continue
    if b == 0xE9:
        rel = struct.unpack_from('<i', buf, i + 1)[0]
        t = (va + 5 + rel) & 0xFFFFFFFF
        if t in TARGETS:
            callers[TARGETS[t]].append((va, 'jmp 0x%X' % t))
        i += 5
        continue
    i += 1

for name, lst in callers.items():
    print('\n=== %s  (%d 处) ===' % (name, len(lst)))
    for a, txt in lst[:40]:
        print('   %08X  %s' % (a, txt))
