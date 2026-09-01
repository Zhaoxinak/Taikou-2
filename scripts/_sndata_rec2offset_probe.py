# -*- coding: utf-8 -*-
"""续163 探索：追「49B 记录字段 → 0x4802e0 的 [esp+0x18] 偏移/尺寸参数」数据依赖。

背景：续162 坐实 0x4802e0 内 `movsx ecx, word ptr [esp+0x18]` 读取 selector 尺寸/资源表偏移，
该值来自其调用方（type-0 簇 handler 0x492e20/0x493140/0x492f80）的帧。本脚本全量反汇编这些
handler，追踪它们如何由 49B 记录算出传入 0x4802e0 的偏移参数。
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
    # 入口：读 [esp+0x18] 的 selector 尺寸来源
    show(0x4802E0, 0x140, '0x4802e0 entry (reads [esp+0x18])')
    # 三个 type-0 簇 handler 全量
    show(0x492E20, 0x260, '0x492e20 type-0 h0 (MAPCHIP)')
    show(0x493140, 0x260, '0x493140 type-0 h1 (MAPCHAR)')
    show(0x492F80, 0x260, '0x492f80 type-0 h2 (SHOP_BG)')
