#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续192 补充：用 raw 4-byte 字面扫描捕捉 0 E8-call-site 函数的「非 E8 调用方」
   （寄存器间接调用 / 跳表目标 / lea+mov 常量）。同时确认跳表 0x49c1cc 自身
   是否仅被 0x49c064 引用（隔离性 => 共享库特征）。
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
TARGETS=[0x49c064,0x49bfba,0x49bfca,0x49bfda,0x49c1cc]

def load():
    with open(BIN,"rb") as f: return f.read()

def raw_literals(b,addr):
    lit=struct.pack("<I",addr);res=[];p=0;n=len(b)
    while True:
        i=b.find(lit,p)
        if i<0: break
        res.append(i+BASE); p=i+1
    return res

def find_e8_calls(b,target):
    res=[];p=0;n=len(b)
    while p<n-5:
        if b[p]==0xE8:
            rel=struct.unpack_from("<i",b,p+1)[0]
            if (p+BASE)+5+rel==target: res.append(p+BASE)
        p+=1
    return res

def main():
    b=load()
    for t in TARGETS:
        e8=find_e8_calls(b,t)
        raw=raw_literals(b,t)
        # 排除函数体内部自身地址
        raw_filtered=[x for x in raw if not (t<=x<t+0x200)]
        print(f"0x{t:x}: E8-calls={len(e8)}  raw-literals(非本体内)={len(raw_filtered)} {[hex(x) for x in raw_filtered[:8]]}")

if __name__=="__main__":
    main()
