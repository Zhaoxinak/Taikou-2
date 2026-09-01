# -*- coding: utf-8 -*-
"""_callers.py — 找所有 e8/call 到给定目标 VA 的函数地址
用法: python scripts/_callers.py 0x466e40"""
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

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

def call_targets():
    """扫描全镜像, 返回 {target_va: set(call_site_va)} 仅对 e8 rel32 直接调用。"""
    res = {}
    i, n = 0, len(MEM) - 5
    while i < n:
        if MEM[i] == 0xE8:
            rel = struct.unpack('<i', MEM[i+1:i+5])[0]
            t = (BASE + i + 5 + rel) & 0xffffffff
            res.setdefault(t, set()).add(BASE + i)
        i += 1
    return res

def main():
    tgt = int(sys.argv[1], 16)
    ct = call_targets()
    sites = sorted(ct.get(tgt, []))
    print(f"目标 {tgt:#x}: {len(sites)} 个直接 e8 调用点")
    # 预构建函数起点集合 (call-target + 0x55 序章)
    fn_starts = set()
    i, n = 0, len(MEM) - 5
    while i < n:
        b = MEM[i]
        if b == 0xE8:
            rel = struct.unpack('<i', MEM[i+1:i+5])[0]
            t = (BASE + i + 5 + rel) & 0xffffffff
            if BASE <= t < BASE + 0x200000: fn_starts.add(t)
        elif b in (0xC3, 0xC2): fn_starts.add(BASE + i + 1)
        elif b == 0xE9:
            rel = struct.unpack('<i', MEM[i+1:i+5])[0]
            t = (BASE + i + 5 + rel) & 0xffffffff
            if t > BASE + i and BASE <= t < BASE + 0x200000: fn_starts.add(t)
        i += 1
    k = 0
    while True:
        p = MEM.find(b'\x55\x89\xe5', k)
        if p < 0: break
        fn_starts.add(BASE + p); k = p + 1
    fl = sorted(fn_starts)
    for s in sites:
        # 找 <=s 的最大函数起点
        fn = None
        for f in fl:
            if f <= s: fn = f
            else: break
        print(f"  call@{s:#x}  (函数≈{fn:#x})")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
