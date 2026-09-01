# -*- coding: utf-8 -*-
"""续162 探索：payload 解析引擎 0x4ec8c0/0x492800/0x4f40b0/0x4802e0 反汇编探针。"""
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


def dis(va, n):
    return list(md.disasm(MEM[va - BASE: va - BASE + n], va))


def show(va, n, label):
    print(f'===== {label} @0x{va:06x} (len {n}) =====')
    for i in dis(va, n):
        print(f'  0x{i.address:06x}  {i.mnemonic} {i.op_str}')
    print()


if __name__ == '__main__':
    # 选择器构造器
    show(0x4EC8C0, 0x60, '0x4ec8c0 selector ctor')
    # 转发
    show(0x492800, 0x30, '0x492800 forwarder')
    # 实际注册
    show(0x4F40B0, 0x80, '0x4f40b0 register')
    # payload 解析入口
    show(0x4802E0, 0x120, '0x4802e0 payload parse entry')
    # type-0 簇（看它怎么调 0x4802e0 / 0x4ec8c0 / 0x492800）
    show(0x492E20, 0x200, '0x492e20 type-0 cluster')
