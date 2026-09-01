#!/usr/bin/env python3

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
# Disassemble the battle draw region 0x423900..0x423e00 (reads objects
# 0x524978 / 0x524990) to extract tile width/height used for HKMAP/HJMAP.
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BASE = 0x400000
data = open(_ROOT + '/scripts/_unpacked_mem.bin', "rb").read()

def disasm(lo, hi):
    chunk = data[(lo-BASE):(hi-BASE)]
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    return [(i.address, i.mnemonic, i.op_str) for i in md.disasm(chunk, lo)]

# Find function start: scan backward from a ref for a prologue.
def fn_start(ref):
    o = ref - BASE
    # search back up to 0x200 for 'push ebp; mov ebp,esp' or 'sub esp,imm'
    for j in range(o, max(0, o-0x300), -1):
        if data[j] == 0x55 and data[j+1] == 0x8b and data[j+2] == 0xec:
            return j + BASE
        if data[j] == 0x83 and data[j+1] == 0xec:  # sub esp, imm8
            return j + BASE
    return o + BASE

# refs to 0x524978 and 0x524990 in 0x423xxx
def refs_to(va):
    pats = [bytes([0xb8])+struct.pack('<I',va), bytes([0xb9])+struct.pack('<I',va),
            bytes([0xbb])+struct.pack('<I',va), bytes([0xbf])+struct.pack('<I',va)]
    hits=[]
    for p in pats:
        s=0
        while True:
            i=data.find(p,s)
            if i<0: break
            hits.append(i+BASE); s=i+1
    return sorted(set(hits))

for obj,label in [(0x524978,"MAIN(0x524978)"),(0x524990,"HKMAP(0x524990)")]:
    rs = [r for r in refs_to(obj) if 0x423900 <= r <= 0x423e00]
    print(f"\n### refs to {label} in 0x4239xx..0x423exx: {len(rs)}")
    for r in rs[:6]:
        s = fn_start(r)
        print(f"  ref@0x{r:06x}  fn starts@0x{s:06x}")
        for a,m,o in disasm(s, min(s+0x120, r+0x40)):
            tag = "  <<<" if a==r else ""
            print(f"    0x{a:06x}: {m} {o}{tag}")
