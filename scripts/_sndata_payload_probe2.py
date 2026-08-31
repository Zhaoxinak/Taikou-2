# -*- coding: utf-8 -*-
"""续162 探索2：0x4ec948 跳表 / 0x4fb07c 分配器指针 / 0x441330/0x441360 资源读取器。"""
import os, struct
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

BASE = 0x400000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(ROOT, 'scripts', '_unpacked_mem.bin'), 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def rd(va, n):
    return MEM[va - BASE: va - BASE + n]


def dump(va, n, label):
    print(f'===== {label} @0x{va:06x} =====')
    for i in range(0, n, 16):
        chunk = rd(va + i, 16)
        hexs = ' '.join(f'{b:02x}' for b in chunk)
        asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f'  0x{va + i:06x}: {hexs}  | {asc}')
    print()


def dis(va, n):
    return list(md.disasm(rd(va, n), va))


def show(va, n, label):
    print(f'===== {label} @0x{va:06x} =====')
    for i in dis(va, n):
        print(f'  0x{i.address:06x}  {i.mnemonic} {i.op_str}')
    print()


if __name__ == '__main__':
    # 跳表 0x4ec948：4 个 dword 目标
    print('=== 0x4ec948 jmp 表 (4×4B) ===')
    tbl = rd(0x4EC948, 16)
    for k in range(4):
        tgt = struct.unpack_from('<I', tbl, k * 4)[0]
        print(f'  case {k} -> 0x{tgt:06x}')
    print()

    # 分配器/注册函数指针 0x4fb07c
    fp = struct.unpack_from('<I', rd(0x4FB07C, 4), 0)[0]
    print(f'=== 0x4fb07c = 0x{fp:06x} (registered allocator/loader) ===')
    show(fp, 0x40, f'registered fn @0x{fp:06x}')

    # 资源读取器 0x441330 / 0x441360（handler 簇用它填游戏表）
    show(0x441330, 0x60, '0x441330 resource reader A')
    show(0x441360, 0x60, '0x441360 resource reader B')

    # 失败路径 0x47bde0
    show(0x47BDE0, 0x30, '0x47bde0 fail-path')

    # 多 dump 几个簇 handler 看它们怎么调 0x4802e0 与读 0x522ca0
    show(0x493140, 0x60, '0x493140 cluster handler')
    show(0x48cc20, 0x60, '0x48cc20 cluster handler')
