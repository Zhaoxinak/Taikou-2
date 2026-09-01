# -*- coding: utf-8 -*-
"""
穷举：单挑伤害值 word[0x5149a8] 与档位 word[0x5149a4] 的**所有写入点**。
常规路径 0x4698d0 只能产出 0..4，而台词分档有 9-24 / >24 两档 ⇒
若存在第二处写入大额值，即为「一击必杀/击中要害」路径。

映像：_unpacked_mem.bin 平坦映射 off = va - 0x400000
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

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_MEM, X86_OP_IMM

BASE = 0x400000
IMG = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()

TARGETS = {
    0x5149a8: '伤害值 word[0x5149a8]',
    0x5149a4: '档位   word[0x5149a4]',
    0x5149ac: '0x5149ac',
}

cs = Cs(CS_ARCH_X86, CS_MODE_32)
cs.detail = True

hits = {k: [] for k in TARGETS}

va = BASE
end = BASE + len(IMG)
while va < end:
    off = va - BASE
    chunk = IMG[off:off + 0x1000]
    if not chunk:
        break
    n = 0
    for ins in cs.disasm(chunk, va):
        n += 1
        # 只看写内存指令
        if ins.mnemonic not in ('mov', 'add', 'sub', 'or', 'and', 'xor', 'imul', 'inc', 'dec', 'shl', 'shr'):
            continue
        ops = ins.operands
        if not ops:
            continue
        dst = ops[0]
        if dst.type != X86_OP_MEM:
            continue
        m = dst.mem
        # 绝对地址且无索引
        if m.base == 0 and m.index == 0 and m.disp:
            for t in TARGETS:
                if m.disp == t:
                    hits[t].append((ins.address, ins.mnemonic, ins.op_str))
    va += 0x1000 if n else 1

for t in sorted(TARGETS):
    hs = hits[t]
    print('=' * 74)
    print('%s  →  %d 处写入/修改' % (TARGETS[t], len(hs)))
    print('=' * 74)
    for a, mn, s in hs:
        # 判定是否为「写大立即数」
        tag = ''
        for op in ([o for o in [None]] ):
            pass
        print('  0x%X  %-6s %s' % (a, mn, s))
    print()

# 额外：找出所有把立即数写进 0x5149a8 的（大额候选）
print('=' * 74)
print('★ 直接给 0x5149a8 写立即数的位置（大额伤害候选）')
print('=' * 74)
va = BASE
while va < end:
    off = va - BASE
    chunk = IMG[off:off + 0x1000]
    if not chunk:
        break
    n = 0
    for ins in cs.disasm(chunk, va):
        n += 1
        if ins.mnemonic not in ('mov',):
            continue
        ops = ins.operands
        if len(ops) != 2:
            continue
        dst, src = ops
        if dst.type != X86_OP_MEM or src.type != X86_OP_IMM:
            continue
        m = dst.mem
        if m.base == 0 and m.index == 0 and m.disp in TARGETS:
            print('  0x%X  mov %s, 0x%x   ← 立即数 %d' % (
                ins.address, ins.op_str.split(',')[0], src.imm, src.imm))
    va += 0x1000 if n else 1
