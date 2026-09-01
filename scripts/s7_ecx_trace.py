#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回溯 +0x0f setter 调用点的 ecx 来源，确认是否 = S7 每城表条目 (base 0x516a28, stride 16)。
   若 ecx 由 `lea ecx,[base+16*idx]` 或等价方式从 S7 表基址派生 => 坐实 S7 专属。
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

import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE=0x400000
BIN=_ROOT + '/scripts/_unpacked_mem.bin'
# 选代表性 call-site：push 0xc(SNDATA 默认哨兵，最可能为 S7 init) / push ebx / push 0
SITES=[0x4b4a7b, 0x4702bd, 0x4511e5, 0x4511ee, 0x4702c6]

def load():
    with open(BIN,"rb") as f: return f.read()

def disasm_back(b, va, nbytes=120):
    md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=False
    off=va-BASE
    start=max(0,off-nbytes)
    return [(i.address,i.mnemonic,i.op_str) for i in md.disasm(b[start:off+6], start+BASE)]

def main():
    b=load()
    for site in SITES:
        print(f"\n===== call-site 0x{site:x} (向前 120B) =====")
        d=disasm_back(b,site)
        # 只打印含 ecx / 0x516a28 / lea / mov 的关键行
        for (a,m,o) in d:
            if ("ecx" in o) or ("0x516a28" in o) or (m=="lea") or ("0x51" in o) or (m in ("add","mov") and "ecx" in m):
                tag=""
                if "0x516a28" in o: tag=" <== S7 BASE"
                if "0x516a" in o: tag=" <== S7-ish"
                print(f"  0x{a:x}: {m} {o}{tag}")

if __name__=="__main__":
    main()
