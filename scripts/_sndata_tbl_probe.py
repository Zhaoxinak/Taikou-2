# -*- coding: utf-8 -*-
"""P0-(A) 验证候选表 @0x501004 是否为 SNDATA 49B 记录的 type->handler 分发表。

决定性判据：handler 内部是否读记录 payload 缓冲 0x522c88（由 0x47fc60 扇出器装入）。
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
import struct
import sys

from capstone import CS_ARCH_X86, CS_MODE_32, Cs

BASE = 0x400000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(ROOT, 'scripts', _ROOT + '/scripts/_unpacked_mem.bin'), 'rb').read()

TBL = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x501004
N = int(sys.argv[2]) if len(sys.argv) > 2 else 153

# 记录缓冲（0x47fc60 扇出目标）
BUF = {0x522C88, 0x522C60, 0x522C70}


def u32(va):
    return struct.unpack_from('<I', MEM, va - BASE)[0]


def disas_at(va, nbytes=96):
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    return list(md.disasm(MEM[va - BASE: va - BASE + nbytes], va))


def ins_touches(ins, addrs):
    """指令操作数是否触及给定绝对地址集。"""
    txt = f'{ins.mnemonic} {ins.op_str}'
    for a in addrs:
        if f'{a:#x}' in ins.op_str or f'{a:#08x}' in ins.op_str:
            return True
    # 也检查立即数等于地址本身（mov eax, 0x522c88 形式）
    try:
        for op in ins.operands:
            if op.type == 2 and op.imm in addrs:  # X86_OP_IMM
                return True
    except Exception:
        pass
    return False


def main():
    ents = [u32(TBL + 4 * i) for i in range(N)]
    print(f'=== 候选表 @{TBL:#x}  n={N} ===')
    print(f'  首项 {ents[0]:#x}  末项 {ents[-1]:#x}')
    deltas = [ents[i + 1] - ents[i] for i in range(N - 1)]
    from collections import Counter
    print(f'  相邻间隔 Top8: {Counter(deltas).most_common(8)}')
    print(f'  负间隔数(=非单调): {sum(1 for d in deltas if d < 0)}')
    print()

    hit = []
    for i, va in enumerate(ents):
        ins = disas_at(va, 112)
        if not ins:
            continue
        touched = sorted({a for a in BUF
                          for x in ins if ins_touches(x, {a})})
        if touched:
            hit.append((i, va, touched, ins))

    print(f'=== 读记录缓冲(0x522c88/60/70)的 handler: {len(hit)}/{N} ===')
    for i, va, touched, ins in hit[:12]:
        print(f'  [{i:3d}] {va:#08x}  触及 {[hex(t) for t in touched]}')
        for x in ins[:6]:
            mark = ' <<<' if any(t in x.op_str for t in
                                 (f'{t:#x}' for t in touched)) or \
                any(t in x.op_str for t in (f'{t:#08x}' for t in touched)) else ''
            print(f'        {x.address:#08x}  {x.mnemonic:<8s} {x.op_str}{mark}')
        print()
    print(f'  ... 共 {len(hit)} 个 handler 读记录缓冲')

    # 未触及缓冲的 handler 抽样
    miss = [(i, va) for i, va in enumerate(ents)
            if not any(ins_touches(x, BUF) for x in disas_at(va, 112))]
    print(f'\n=== 未触及缓冲的 handler: {len(miss)}/{N}（抽样前 10）===')
    for i, va in miss[:10]:
        ins = disas_at(va, 48)
        head = f'{ins[0].mnemonic} {ins[0].op_str}' if ins else '(无法反汇编)'
        print(f'  [{i:3d}] {va:#08x}  {head}')


if __name__ == '__main__':
    main()
