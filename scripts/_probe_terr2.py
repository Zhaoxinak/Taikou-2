# -*- coding: utf-8 -*-

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
# 精确 5 字节模式定位 0x5179b8 真实引用
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', "rb").read()
BASE = 0x400000
N = len(MEM)
cs = Cs(CS_ARCH_X86, CS_MODE_32)
cs.detail = True

# 模式: (bytes, 描述)
PATS = [
    (bytes([0x81,0xe9,0xb8,0x79,0x51,0x00]), "sub ecx,0x5179b8"),
    (bytes([0x81,0xe8,0xb8,0x79,0x51,0x00]), "sub eax,0x5179b8"),
    (bytes([0x81,0xea,0xb8,0x79,0x51,0x00]), "sub edx,0x5179b8"),
    (bytes([0xb8,0xb8,0x79,0x51,0x00]), "mov eax,0x5179b8"),
    (bytes([0xb9,0xb8,0x79,0x51,0x00]), "mov ecx,0x5179b8"),
    (bytes([0x8d,0x1d,0xb8,0x79,0x51,0x00]), "lea ebx,[0x5179b8]"),
    (bytes([0x8d,0x15,0xb8,0x79,0x51,0x00]), "lea edx,[0x5179b8]"),
]
hits = []  # (addr_of_pattern_start, desc)
for pat, desc in PATS:
    L = len(pat)
    i = 0
    while i + L <= N:
        if MEM[i:i+L] == pat:
            hits.append((BASE + i, desc))
        i += 1
print(f"精确 0x5179b8 引用: {len(hits)}")
# 去重相邻
seen=set(); uniq=[]
for a,d in hits:
    if a in seen: continue
    seen.add(a); uniq.append((a,d))
print(f"去重后: {len(uniq)}")
for a,d in uniq:
    print(f"  0x{a:08x}  {d}")
