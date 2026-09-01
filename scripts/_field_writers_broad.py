# -*- coding: utf-8 -*-
"""_field_writers_broad.py — 全镜像扫描对给定字段偏移的「写」内存访问（不限表基址符号）。
用法: python scripts/_field_writers_broad.py <offs...>
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

import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
CODE_LO, CODE_HI = 0x400000, 0x600000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
def off(va): return va - BASE
WR_MNEM = {'mov', 'add', 'sub', 'or', 'and', 'xor', 'inc', 'dec', 'shl', 'shr'}

def build_fn_bounds():
    fn_starts = set()
    i, n = 0, len(MEM) - 5
    while i < n:
        b = MEM[i]
        if b == 0xE8:
            rel = struct.unpack('<i', MEM[i+1:i+5])[0]
            t = (BASE + i + 5 + rel) & 0xffffffff
            if CODE_LO <= t < CODE_HI: fn_starts.add(t)
        elif b in (0xC3, 0xC2): fn_starts.add(BASE + i + 1)
        elif b == 0xE9:
            rel = struct.unpack('<i', MEM[i+1:i+5])[0]
            t = (BASE + i + 5 + rel) & 0xffffffff
            if t > BASE + i and CODE_LO <= t < CODE_HI: fn_starts.add(t)
        i += 1
    k = 0
    while True:
        p = MEM.find(b'\x55\x89\xe5', k)
        if p < 0: break
        fn_starts.add(BASE + p); k = p + 1
    fl = sorted(fn_starts)
    nxt = {}
    for i2 in range(len(fl)):
        nxt[fl[i2]] = fl[i2+1] if i2+1 < len(fl) else fl[i2] + 0x800
    return fl, nxt

def disasm_fn(va, max_bytes):
    end = va + max_bytes; cur = va; out = []
    while cur < end:
        chunk = MEM[off(cur):off(end)]
        got = list(md.disasm(chunk, cur))
        if not got: cur += 1; continue
        for ins in got:
            if ins.address >= end: break
            out.append(ins)
        last = out[-1]; nxt = last.address + last.size
        cur = nxt if nxt > cur else cur + 1
    return out

def main():
    targets = [int(x, 16) for x in sys.argv[1:]]
    fl, fn_next = build_fn_bounds()
    hits = {t: [] for t in targets}
    for fn in fl:
        nxt = fn_next[fn]
        if nxt - fn > 0x800: nxt = fn + 0x800
        for ins in disasm_fn(fn, nxt - fn):
            for o in ins.operands:
                if (o.type == CS_OP_MEM and o.mem.base and o.mem.index == 0
                        and o.mem.disp in targets):
                    m = ins.mnemonic
                    is_w = (m in WR_MNEM and ins.operands and ins.operands[0].type == CS_OP_MEM)
                    if is_w:
                        hits[o.mem.disp].append((ins.address, m, ins.op_str))
    for t in targets:
        print(f"\n=== +{t:#05x} ({t}) 写访问 : {len(hits[t])} 处 ===")
        for addr, m, ops in sorted(hits[t]):
            print(f"  0x{addr:x}: {m} {ops}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
