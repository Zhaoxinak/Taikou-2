# -*- coding: utf-8 -*-
"""续241 勘察 #3：宿主函数调用方与 push 实参（临时探针）"""
import os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, x86_const as X

BASE = 0x400000
HERE = os.path.dirname(os.path.abspath(__file__))
MEM = open(os.path.join(HERE, '_unpacked_mem.bin'), 'rb').read()
MD = Cs(CS_ARCH_X86, CS_MODE_32); MD.skipdata = True; MD.detail = True

TARGETS = [0x458e20, 0x45d950, 0x448990, 0x447230, 0x45ade0, 0x442d70, 0x451f90]

insns = list(MD.disasm(MEM, BASE))
for t in TARGETS:
    print('=' * 90)
    print('CALLERS of 0x%06x' % t)
    calls = [x for x in insns if x.mnemonic == 'call' and len(x.operands) == 1
             and x.operands[0].type == X.X86_OP_IMM and x.operands[0].imm == t]
    for c in calls:
        # 回溯取调用点前 8 条指令（边界对齐：从 c.address-0x20 起线性 disasm 到 call）
        print('  caller @0x%06x:' % c.address)
        start = c.address - 0x20
        seg = list(MD.disasm(MEM[start - BASE: c.address - BASE + c.size], start))
        for x in seg[-9:]:
            print('    0x%06x %-7s %s' % (x.address, x.mnemonic, x.op_str))
