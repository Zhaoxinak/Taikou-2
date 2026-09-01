#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续172 下一步(A)：dump 两个相性入口的差异化 call 站点上下文，定玩法语义。"""
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
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()

def dis(va, n):
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.skipdata = True
    off = va - BASE
    return list(md.disasm(bytes(MEM[off:off+n]), va))

def dump_window(va, site, before=8, after=14):
    """打印 site 前 before 条、后 after 条指令。"""
    code = dis(va, 0xa00)
    idx = next((i for i, ins in enumerate(code) if ins.address == site), None)
    if idx is None:
        print(f"  [site {hex(site)} 不在解码窗口]")
        return
    lo = max(0, idx-before); hi = min(len(code), idx+after)
    for ins in code[lo:hi]:
        mark = "  >>" if ins.address == site else "    "
        print(f"  {mark} 0x{ins.address:06x}  {ins.mnemonic}  {ins.op_str}")

print("############### 0x4a5010 (相性登用/引抜 A) 独有站点 ###############")
for site in [0x4a5189, 0x4a5328]:  # 0x49a730 bit7 setter
    print(f"\n--- call 0x49a730 (bit7 setter) @0x{site:06x} ---")
    dump_window(0x4a5010, site)
for site in [0x4a527a]:  # 0x49a800 (bit11 setter, +0x2d bit3)
    print(f"\n--- call 0x49a800 @0x{site:06x} ---")
    dump_window(0x4a5010, site)

print("\n\n############### 0x4a5370 (相性引抜/寢返し B) 独有站点 ###############")
for site in [0x4a5bf2, 0x4a5d05]:  # 0x4ebcd0 sat_sub
    print(f"\n--- call 0x4ebcd0 (sat_sub) @0x{site:06x} ---")
    dump_window(0x4a5370, site)
for site in [0x4a5ba1]:  # 0x4ebc50 muldiv
    print(f"\n--- call 0x4ebc50 (muldiv) @0x{site:06x} ---")
    dump_window(0x4a5370, site)
for site in [0x4a5c0c, 0x4a5c2d, 0x4a5ca8, 0x4a5cb0, 0x4a5ce9]:  # 0x4a33xx 资源 wrapper
    print(f"\n--- call 0x{dis(site,1)[0].op_str} @0x{site:06x} ---")
    dump_window(0x4a5370, site)
