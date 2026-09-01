#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""精确抽取 S6 (0x516610) 的 LOAD 0x47e770 / SAVE 0x47e8a0 字段序列。

字段注册/读写原语（已反汇编坐实）：
  0x47d910(ptr) = 从流读 1 字节 -> byte[ptr]     (读原语 0x47da10)
  0x47d930(ptr) = 从流读 2 字节 -> word[ptr]     (读原语 0x47da50)
  0x47dac0(val) = 写 4 字节到流（SAVE 侧）
  0x47da80(val) = 写 1 字节到流（SAVE 侧）
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

import re, struct, sys, json
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMG = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
S6 = 0x516610

LOAD_RD = {0x47d910: 'B', 0x47d930: 'W'}
SAVE_WR = {0x47dac0: 'D', 0x47da80: 'B', 0x47da90: 'W', 0x47daa0: 'W'}


def dis(va, n):
    off = va - BASE
    return list(md.disasm(IMG[off:off + n], va))


def load_fields(va=0x47e770, until=0x47e89f):
    """LOAD: 模式 push imm32(地址) ; mov ecx,esi ; call 0x47d910/0x47d930"""
    ins = dis(va, until - va)
    out = []
    for i, b in enumerate(ins):
        if b.mnemonic != 'call':
            continue
        t = b.operands[0].imm
        if t not in LOAD_RD:
            continue
        # 回找最近的 push imm32
        a = None
        for j in range(i - 1, max(-1, i - 4), -1):
            p = ins[j]
            if p.mnemonic == 'push' and p.operands[0].type == 2 and p.operands[0].imm >= 0x400000:
                a = p.operands[0].imm
                break
        if a is None:
            continue
        out.append((a - S6, LOAD_RD[t], b.address))
    return out


def save_fields(va=0x47e8a0, n=0x220):
    """SAVE: 模式 mov reg, [abs] ; (mov [esp+4],..) ; push ; call 0x47dac0/0x47da80"""
    ins = dis(va, n)
    out = []
    for i, b in enumerate(ins):
        if b.mnemonic != 'call':
            continue
        t = b.operands[0].imm
        if t not in SAVE_WR:
            continue
        # 回找最近的 mov reg, [abs]
        a = None
        for j in range(i - 1, max(-1, i - 6), -1):
            p = ins[j]
            if p.mnemonic == 'mov' and len(p.operands) == 2 and p.operands[1].type == 3:
                m = p.operands[1].mem
                if m.base == 0 and m.index == 0 and m.disp >= S6:
                    a = m.disp
                    w = {1: 'B', 2: 'W', 4: 'D'}[p.operands[1].size]
                    break
        if a is None:
            continue
        out.append((a - S6, w, SAVE_WR[t], b.address))
    return out


if __name__ == '__main__':
    lf = load_fields()
    print(f'=== LOAD 0x47e770 : {len(lf)} 个字段 ===')
    tot = 0
    for off, w, va in lf:
        tot += {'B': 1, 'W': 2}[w]
        print(f'  +{off:02x}  {w}   @0x{va:x}')
    print(f'  流字节合计 = {tot}')

    sf = save_fields()
    print(f'\n=== SAVE 0x47e8a0 : {len(sf)} 个字段 ===')
    for off, rw, ww, va in sf:
        print(f'  +{off:02x}  read{rw} write{ww}  @0x{va:x}')

    json.dump(dict(load=[(o, w, v) for o, w, v in lf],
                   save=[(o, r, w, v) for o, r, w, v in sf]),
              open(_ROOT + '/scripts/s6_layout.json', 'w'), indent=1)
    print('\n-> scripts/s6_layout.json')
