# -*- coding: utf-8 -*-
"""找 4 字节绝对地址立即数的所有引用点，并反汇编上下文。
用法: python _xref4.py 0x504b28 [--ctx 8]"""
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
from capstone import *
BASE = 0x400000
mem = open(_ROOT + '/scripts/_unpacked_mem.bin','rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

target = int(sys.argv[1], 16)
ctx = 8
if '--ctx' in sys.argv:
    ctx = int(sys.argv[sys.argv.index('--ctx') + 1])
pat = struct.pack('<I', target)
hits = []
i = 0
while True:
    i = mem.find(pat, i)
    if i < 0: break
    hits.append(i)
    i += 1
print(f'{target:#x} 出现 {len(hits)} 次')
for off in hits:
    va = BASE + off
    # 向上回溯到一条指令边界（最多 16 字节）
    start = max(0, off - 16)
    # 线性反汇编 [start, off+8)，找到覆盖 off 的指令
    found = None
    for s in range(start, off + 1):
        for ins in md.disasm(mem[s:off + 8], BASE + s):
            if ins.address <= va < ins.address + ins.size:
                found = (s, ins)
                break
        if found: break
    print('----')
    if not found:
        print(f'  @{va:#x} (无法对齐)  上下文字节: {mem[off-8:off+8].hex()}')
        continue
    s, ins = found
    # 打印该指令前后各 ctx 条
    block = mem[max(0, s - 24): s + 4 + 24]
    bstart = BASE + max(0, s - 24)
    seq = list(md.disasm(block, bstart))
    lo = max(0, s - 24); 
    for k, ii in enumerate(seq):
        mark = '>>>' if ii.address == ins.address else '   '
        print(f'  {mark} {ii.address:#x}  {ii.bytes.hex():<16} {ii.mnemonic:<7} {ii.op_str}')
