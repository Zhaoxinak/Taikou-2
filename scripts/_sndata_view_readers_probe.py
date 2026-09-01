# -*- coding: utf-8 -*-
"""续165 探索①：窗口扫描代码段 0x400000..0x5A0000，找 3 视图缓冲 0x522c88/0x522c60/0x522c70 引用。"""
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

import os
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

BASE = 0x400000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(ROOT, 'scripts', _ROOT + '/scripts/_unpacked_mem.bin'), 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

VIEWS = ['0x522c88', '0x522c60', '0x522c70']
CODE_END = 0x5A0000


def main():
    hits = []
    va = BASE
    while va < CODE_END:
        chunk = MEM[va - BASE: va - BASE + 0x2000]
        for ins in md.disasm(chunk, va):
            s = f'{ins.mnemonic} {ins.op_str}'
            for v in VIEWS:
                if v in s:
                    hits.append((ins.address, ins.mnemonic, ins.op_str))
                    break
        va += 0x2000
    print(f'=== 3 视图缓冲引用共 {len(hits)} 处 ===')
    for addr, mn, op in hits:
        is_write = (',' in op) and (']' in op.split(',')[0])
        tag = 'W' if is_write else 'R'
        print(f'  0x{addr:06x}  [{tag}] {mn} {op}')
    readers = [(a, m, o) for (a, m, o) in hits if not (',' in o and ']' in o.split(',')[0])]
    print(f'\n=== 读取方(R) 共 {len(readers)} 处 ===')
    for a, m, o in readers:
        print(f'  0x{a:06x}  {m} {o}')


if __name__ == '__main__':
    main()
