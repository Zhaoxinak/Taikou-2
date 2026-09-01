# -*- coding: utf-8 -*-
"""
精确定位 set_rank(0x49a7e0) 调用的**立即数参数**。
set_rank 是 __fastcall(ecx=this) + stdcall(1 参数, ret 4)，
典型模式：  push <imm> / mov ecx, esi / call 0x49a7e0
重点抓参数 == 7 (大名) / 8 (城主)。
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
from capstone.x86 import X86_OP_IMM

BASE = 0x400000
IMG = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
SET_RANK = 0x49a7e0

cs = Cs(CS_ARCH_X86, CS_MODE_32)
cs.detail = True

# 先找所有 call set_rank 的调用点
call_sites = []
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
        if ins.mnemonic == 'call':
            for op in ins.operands:
                if op.type == X86_OP_IMM and op.imm == SET_RANK:
                    call_sites.append(ins.address)
    va += 0x1000 if n else 1

print('call set_rank 调用点 %d 处；逐个回溯参数 push：' % len(call_sites))
print('=' * 74)

hits78 = []
for a in call_sites:
    # 回溯 48 字节
    start = max(BASE, a - 0x30)
    d = IMG[start - BASE:a - BASE]
    ins_list = list(cs.disasm(d, start))
    # 找 call 之前最近的 push imm（从后往前找，最多回看 4 条）
    arg = None
    arg_addr = None
    for ins in reversed(ins_list):
        if ins.address >= a:
            continue
        if ins.mnemonic == 'push':
            for op in ins.operands:
                if op.type == X86_OP_IMM:
                    arg = op.imm
                    arg_addr = ins.address
                    break
            break
        if ins.mnemonic in ('ret', 'jmp', 'call'):
            break
    flag = ''
    if arg in (7, 8):
        flag = '  ★★★ rank=%d %s' % (arg, '(大名)' if arg == 7 else '(城主)')
        hits78.append((a, arg))
    print('  call@0x%X   arg=%s%s' % (a, ('%d' % arg) if arg is not None else '(寄存器/变量)', flag))

print()
print('=' * 74)
print('★ set_rank 传立即数 7/8 的调用点：')
for a, r in hits78:
    print('    0x%X  set_rank(%d)  %s' % (a, r, '大名' if r == 7 else '城主'))
