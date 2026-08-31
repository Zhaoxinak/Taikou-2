# -*- coding: utf-8 -*-
"""P0-(A) 扫描脚本：SNDATA 49B 记录分派器 0x47ff68 + 主循环 0x4e8625/0x4e89cd。

目标：找「按记录类型索引的函数指针表 / 两级跳表」，建 type -> handler 全映射。
用法：
    python scripts/_sndata_dispatch_scan.py dis 0x47ff68 120
    python scripts/_sndata_dispatch_scan.py dis 0x4e8600 80
    python scripts/_sndata_dispatch_scan.py switch 0x47ff68 200
"""
import os
import struct
import sys

from capstone import CS_ARCH_X86, CS_MODE_32, Cs

BASE = 0x400000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(ROOT, 'scripts', '_unpacked_mem.bin'), 'rb').read()


def rd(va, n):
    return MEM[va - BASE: va - BASE + n]


def u32(va):
    return struct.unpack('<I', rd(va, 4))[0]


def u16(va):
    return struct.unpack('<H', rd(va, 2))[0]


def disas(va, n=80):
    """从 va 起线性反汇编 n 条指令（capstone 现场扫，物化 list 避免共享 Cs 状态坑）。"""
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    chunk = rd(va, n * 8)
    out = list(md.disasm(chunk, va))
    return out[:n]


def show(ins_list, maxn=200):
    for i in ins_list[:maxn]:
        print(f'  {i.address:#08x}  {i.mnemonic:<8s} {i.op_str}')
    print()


SWITCH_MN = {'jmp', 'call'}


def find_switch(va, n=250):
    """在 va 起 n 条指令内找跳表/分派特征。"""
    ins = disas(va, n)
    hits = []
    for k, i in enumerate(ins):
        # jmp/call [reg*4 + imm32]  —— dword 函数指针表
        if i.mnemonic in SWITCH_MN and i.op_str.startswith('dword ptr ['):
            hits.append(('DWORD_TABLE', k, i.address, i.mnemonic, i.op_str))
        # mov reg, byte ptr [reg + imm32] —— 一级 byte 压缩映射表
        if i.mnemonic == 'mov' and 'byte ptr [' in i.op_str and i.op_str.startswith('d') is False:
            if ', byte ptr [' in i.op_str:
                hits.append(('BYTE_MAP', k, i.address, i.mnemonic, i.op_str))
        # cmp reg, imm ; ja —— 上界检查
        if i.mnemonic in ('cmp',) and k + 1 < len(ins) and ins[k + 1].mnemonic in ('ja', 'jbe', 'jae', 'jb'):
            hits.append(('BOUND', k, i.address, f'{i.mnemonic} {i.op_str}',
                         f'{ins[k+1].mnemonic} {ins[k+1].op_str}'))
    return hits


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == 'dis':
        va = int(sys.argv[2], 16)
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 80
        print(f'=== disas {va:#x} ({n} insns) ===')
        show(disas(va, n))
    elif cmd == 'switch':
        va = int(sys.argv[2], 16)
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 250
        print(f'=== switch patterns in {va:#x} ({n} insns) ===')
        hits = find_switch(va, n)
        if not hits:
            print('  (none)')
        for tag, k, addr, a, b in hits:
            print(f'  [{tag:11s}] #{k:<3d} {addr:#08x}  {a}  |  {b}')
        print(f'\n  total {len(hits)}')
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
