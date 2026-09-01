# -*- coding: utf-8 -*-
"""_dis_fn.py — 反汇编给定地址所在函数（用 build_fn_bounds 定界）。
用法: python scripts/_dis_fn.py 0xADDR1 0xADDR2 ...
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

def main():
    fl, fn_next = build_fn_bounds()
    for arg in sys.argv[1:]:
        target = int(arg, 16)
        # 找起始 <= target 的最大 fn
        fn = None
        for f in fl:
            if f <= target: fn = f
            else: break
        if fn is None:
            print(f"0x{target:x}: 未找到函数边界，直接反汇编 0x100"); fn = target
        nxt = fn_next.get(fn, fn + 0x800)
        end = min(nxt, fn + 0x600)
        print(f'=== fn 0x{fn:x} (target 0x{target:x}) len={end-fn:#x} ===')
        cur = fn
        while cur < end:
            chunk = MEM[off(cur):off(end)]
            got = list(md.disasm(chunk, cur))
            if not got: cur += 1; continue
            for ins in got:
                if ins.address >= end: break
                mark = '  <<<' if ins.address==target else ''
                print(f'  0x{ins.address:x}: {ins.mnemonic} {ins.op_str}{mark}')
            last = got[-1]; nxt2 = last.address + last.size
            cur = nxt2 if nxt2 > cur else cur + 1
        print()
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
