#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
MEM="F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
mem=open(MEM,'rb').read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)

# 搜索战斗地图文件名引用
for needle in [b"HJMAPDAT",b"HBMAP",b"HJMAP",b"HKMAP"]:
    p=0
    hits=[]
    while True:
        q=mem.find(needle,p)
        if q<0: break
        hits.append(q); p=q+1
    if hits:
        print(f"'{needle.decode()}' 命中 {len(hits)} 处:")
        for h in hits[:5]:
            print(f"  0x{h:x} (VA 0x{base+h:08x}) 周围字符串: {mem[max(0,h-4):h+len(needle)+30]}")

# 找到 HJMAPDAT.DAT 的字符串 VA 后，找其引用（4字节LE）
for needle in [b"HJMAPDAT",b"HBMAP"]:
    idx=mem.find(needle)
    if idx<0: continue
    va=base+idx
    # 找引用此 VA 的代码
    tgt=struct.pack("<I",va)
    p=0; refs=[]
    while True:
        q=mem.find(tgt,p)
        if q<0: break
        refs.append(q); p=q+1
    print(f"\n=== 引用 '{needle.decode()}' (VA 0x{va:08x}) 的 {len(refs)} 处代码 ===")
    for r in refs[:3]:
        code=mem[r-50:r+250]
        print(f"\n--- ref @ 0x{base+r:08x} ---")
        for ins in md.disasm(code, base+r-50):
            mark=" >>>" if ins.address==base+r else "    "
            print(f"  0x{ins.address:08x}{mark} {ins.mnemonic} {ins.op_str}")
