#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""参数化立即数 xref：给定若干 VA 常量，列出所有「指令边界包含该立即数」的命中，
并尽量归并到所属函数（最近的、已确认的函数起点）。

用法： python _xref_addr.py 0x519548 0x5179bc 0x47e440
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

import struct, sys, pickle, os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMG = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False
CACHE = _ROOT + '/scripts/_insn_addrs.pkl'


def build_insn_set():
    if os.path.exists(CACHE):
        print('  (复用缓存)', file=sys.stderr)
        return pickle.load(open(CACHE, 'rb'))
    starts = set()
    n = len(IMG)
    for i in range(n - 5):
        if IMG[i] == 0xE8:
            rel = struct.unpack('<i', IMG[i + 1:i + 5])[0]
            tgt = i + 5 + rel
            if 0 <= tgt < n:
                starts.add(tgt)
    print(f'  call-rel32 起点: {len(starts)}', file=sys.stderr)
    insn = {}
    fn_starts = set()
    for s in sorted(starts):
        if s in insn:
            continue
        off = s
        end = min(s + 0x4000, n)
        fn_starts.add(off)
        for ins in md.disasm(IMG[off:end], BASE + off):
            insn[off] = (ins.size, f'{ins.mnemonic} {ins.op_str}')
            off += ins.size
            if ins.mnemonic in ('ret', 'retn', 'retf', 'hlt', 'ud2', 'int3'):
                break
            if off >= end:
                break
    pickle.dump((insn, sorted(fn_starts)), open(CACHE, 'wb'))
    print(f'  指令: {len(insn)}', file=sys.stderr)
    return insn, sorted(fn_starts)


def xref(imm, insn):
    pat = struct.pack('<I', imm)
    out = []
    off = 0
    while True:
        i = IMG.find(pat, off)
        if i < 0:
            break
        hit = None
        for j in range(max(0, i - 7), i + 1):
            if j in insn:
                size, txt = insn[j]
                if j < i < j + size:
                    hit = (i, j, txt)
                    break
                if j == i and size >= 4:
                    hit = (i, j, txt)
                    break
        if hit:
            out.append(hit)
        off = i + 1
    return out


def main():
    targets = [int(a, 0) for a in sys.argv[1:]]
    if os.path.exists(CACHE):
        insn, fn_starts = pickle.load(open(CACHE, 'rb'))
        print('  (复用缓存)', file=sys.stderr)
    else:
        insn, fn_starts = build_insn_set()

    for imm in targets:
        raw = 0
        off = 0
        p = struct.pack('<I', imm)
        while True:
            i = IMG.find(p, off)
            if i < 0:
                break
            raw += 1
            off = i + 1
        real = xref(imm, insn)
        print(f'\n=== 0x{imm:x} : 字节串匹配 {raw} 处, 指令对齐真命中 {len(real)} 处 ===')
        # 归并到函数
        shown = 0
        for hit_off, ins_off, txt in real:
            fn = None
            for fs in reversed(fn_starts):
                if fs <= ins_off:
                    fn = fs
                    break
            print(f'  0x{BASE + ins_off:06x} [fn 0x{BASE + fn:06x}]  {txt}')
            shown += 1
            if shown >= 40 and len(real) > 40:
                print(f'  ... 另有 {len(real) - shown} 处')
                break


if __name__ == '__main__':
    main()
