# -*- coding: utf-8 -*-
"""续160 草稿：追 0x4e8625 / 0x4e89cd 两条主循环对头四字的比较链，
建「类型 → 分支」映射（替代已证伪的 type→handler 函数指针表）。

用法：
  python _sndata_mainloop.py dis   <va> [nbytes]   # 线性反汇编一整段
  python _sndata_mainloop.py cmps   <va> [nbytes]   # 只看 cmp/test + 分支
  python _sndata_mainloop.py fanout <va> [nbytes]   # 看 call 0x47fc60 上下文
"""
import sys, struct
from capstone import CS_ARCH_X86, CS_MODE_32, Cs, CS_OP_IMM

BASE = 0x400000
ROOT = r'F:\Games\Taikou 2'
MEM = open(ROOT + r'\scripts\_unpacked_mem.bin', 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def disasm(va, nbytes):
    off = va - BASE
    return list(md.disasm(MEM[off:off + nbytes], va))


def is_ret(i):
    return i.mnemonic in ('ret', 'retn') or (i.mnemonic == 'ret' and True)


def find_function(va, max_bytes=0x2000):
    """从 va 起线性反汇编，直到遇到 ret（函数返回）。返回指令列表。"""
    off = va - BASE
    out = []
    for i in md.disasm(MEM[off:off + max_bytes], va):
        out.append(i)
        if i.mnemonic == 'ret':
            break
    return out


def cmd_dis(va, nbytes=0x600):
    for i in disasm(va, nbytes):
        tgt = '   ; CALL' if i.mnemonic == 'call' and i.op_str.startswith('0x') else ''
        print(f"0x{i.address:06x}  {i.bytes.hex():<20s} {i.mnemonic:<8s} {i.op_str}{tgt}")


def cmd_cmps(va, nbytes=0x2000):
    """筛 cmp/test + 条件跳 + call 0x47fc60，重建比较链。"""
    insts = find_function(va, nbytes)
    for i in insts:
        if i.mnemonic in ('cmp', 'test') or i.mnemonic.startswith('j'):
            print(f"0x{i.address:06x}  {i.mnemonic:<8s} {i.op_str}")


def cmd_fanout(va, nbytes=0x2000, ctx=80):
    insts = find_function(va, nbytes)
    for k, i in enumerate(insts):
        if i.mnemonic == 'call' and i.op_str == '0x47fc60':
            lo = max(0, k - ctx // 4)
            hi = min(len(insts), k + ctx // 4)
            print(f'===== fan-out call @ 0x{i.address:06x} =====')
            for j in insts[lo:hi]:
                mark = '  <<<' if j.address == i.address else ''
                print(f"0x{j.address:06x}  {j.mnemonic:<8s} {j.op_str}{mark}")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    sub = sys.argv[1]
    va = int(sys.argv[2], 16)
    nbytes = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x600
    if sub == 'dis':
        cmd_dis(va, nbytes)
    elif sub == 'cmps':
        cmd_cmps(va, nbytes)
    elif sub == 'fanout':
        cmd_fanout(va, nbytes)
