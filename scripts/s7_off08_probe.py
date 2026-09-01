#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""确认 +0x08 setter 簇 (0x49bfba/0x49bfff/0x49c064) 是否 S7-entry 专属，
   并统计各自 E8 call-site 计数。共享库陷阱见 续155。
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

BASE = 0x400000
BIN  = _ROOT + '/scripts/_unpacked_mem.bin'
FNS = [0x49bfba, 0x49bfff, 0x49c064]

def load():
    with open(BIN, "rb") as f:
        return f.read()

def disasm_at(b, va, nbytes=48):
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail=False
    off = va-BASE
    return [(i.address,i.mnemonic,i.op_str) for i in md.disasm(b[off:off+nbytes],va)]

def find_e8_calls(b, target):
    off_t=target-BASE; res=[]; p=0; n=len(b)
    while p<n-5:
        if b[p]==0xE8:
            rel=struct.unpack_from("<i",b,p+1)[0]
            if (p+BASE)+5+rel==target: res.append(p+BASE)
        p+=1
    return res

def main():
    b=load()
    for fn in FNS:
        d=disasm_at(b,fn)
        txt=" | ".join(f"{m} {o}" for (_,m,o) in d)
        calls=find_e8_calls(b,fn)
        print(f"0x{fn:x}  calls={len(calls)}  {[hex(c) for c in calls]}")
        print(f"   {txt}\n")

if __name__=="__main__":
    main()
