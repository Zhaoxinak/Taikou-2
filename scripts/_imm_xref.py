#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""严格立即数 xref：只认「落在真实指令边界上」的 4 字节匹配。

方法（对治本项目反复踩中的「落指令中间」伪命中）：
 1. 扫全镜像 E8 rel32(call) 收集函数起点；
 2. 从每个起点线性反汇编至 ret/int3/hlt/非法，收集所有**指令起始地址**；
 3. 4 字节立即数匹配处，仅当该偏移 ∈ 指令起始集合 才算真命中。
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

import struct, sys, json, pickle, os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import *

IMG = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False
CACHE = _ROOT + '/scripts/_insn_addrs.pkl'


def build_insn_set():
    """返回 {指令起始偏移: (size, 'mnemonic op_str')}。
    注意：4 字节立即数落在指令**中间**(操作数)，判定必须用「包含」而非「等于」。"""
    if os.path.exists(CACHE):
        return pickle.load(open(CACHE, 'rb'))
    starts = set()
    n = len(IMG)
    for i in range(n - 5):
        if IMG[i] == 0xE8:
            rel = struct.unpack('<i', IMG[i + 1:i + 5])[0]
            tgt = i + 5 + rel
            if 0 <= tgt < n:
                starts.add(tgt)
    print(f'  call rel32 目标(函数起点候选): {len(starts)}', file=sys.stderr)
    insn = {}
    for s in sorted(starts):
        off = s
        end = min(s + 0x4000, n)
        for ins in md.disasm(IMG[off:end], BASE + off):
            insn[off] = (ins.size, f'{ins.mnemonic} {ins.op_str}')
            off += ins.size
            if ins.mnemonic in ('ret', 'retn', 'retf', 'hlt', 'ud2', 'int3'):
                break
            if off >= end: break
    print(f'  指令(起始->size,text): {len(insn)}', file=sys.stderr)
    pickle.dump(insn, open(CACHE, 'wb'))
    return insn


def xref(imm, insn):
    """返回 [(命中偏移, 指令起始偏移, 指令文本)]，仅保留指令完整**包含**该偏移者。"""
    pat = struct.pack('<I', imm)
    out = []
    off = 0
    while True:
        i = IMG.find(pat, off)
        if i < 0: break
        hit = None
        for j in range(max(0, i - 7), i + 1):      # x86 指令最长 15B，回看 7B 足够定位含 imm32 者
            if j in insn:
                size, txt = insn[j]
                if j < i < j + size:               # 严格包含（排除 j==i 的纯 opcode 巧合）
                    hit = (i, j, txt); break
                if j == i and size >= 4:
                    hit = (i, j, txt); break
        if hit: out.append(hit)
        off = i + 1
    return out


if __name__ == '__main__':
    insn = build_insn_set()
    print(f'指令集合构建完成 ({len(insn)} 条)\n')
    for imm, label in ((0x51dc60, 'S14 blob 基址'),
                       (0x51dc5c, 'blob 前 4B (疑似索引/指针)'),
                       (0x51eb88, '城表(对照, 应大量命中)'),
                       (0x519868, '武将实体表(对照)')):
        raw = 0; off = 0
        p = struct.pack('<I', imm)
        while True:
            i = IMG.find(p, off)
            if i < 0: break
            raw += 1; off = i + 1
        real = xref(imm, insn)
        print(f'0x{imm:x}  {label}')
        print(f'   字节串匹配 {raw:4d} 处 -> 指令对齐真命中 {len(real):4d} 处')
        for off_i, ins_off, txt in real[:8]:
            print(f'      0x{BASE + ins_off:x}: {txt}')
        print()
