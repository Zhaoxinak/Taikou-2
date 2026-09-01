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
# 找物品定义表(189×19)的读取/索引函数：搜索循环边界 189(0xbd) 与 ×19(stride) 索引。
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BIN = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
data = open(BIN,"rb").read()
def off(va): return va-BASE
cs = Cs(CS_ARCH_X86, CS_MODE_32); cs.detail=True

# 候选：cmp eax/ecx/edx, 0xbd (189)
pats = [b"\x3d\xbd\x00\x00\x00", b"\x83\xf8\xbd", b"\x83\xf9\xbd", b"\x83\xfa\xbd", b"\x81\xf8\xbd\x00\x00\x00"]
hits = []
for p in pats:
    start=0
    while True:
        i = data.find(p, start)
        if i<0: break
        hits.append(i); start=i+1

print(f"189-bound hits: {len(hits)}")
for i in hits:
    va = BASE+i
    code = data[i-0x60:i+8]
    print(f"\n----- cmp 189 @ {va:#08x} -----")
    for ins in cs.disasm(code, va-0x60):
        print(f"{ins.address:#08x}  {ins.mnemonic} {ins.op_str}")
