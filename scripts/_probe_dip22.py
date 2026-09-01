# -*- coding: utf-8 -*-
"""完整 dump 结算主函数 0x4b9250 区域, 高亮所有 setter/getter 调用及其参数上下文."""
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

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
mem = open(MEM_PATH, "rb").read()
N = len(mem)
def rva(p): return p - BASE

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

# 结算链路覆盖 0x4b8f70 .. 0x4ba200
START, END = 0x4b8f70, 0x4ba200
code = mem[rva(START): rva(END)]

# 先扫描该区域所有 call 目标, 标记 setter/getter
TARGETS = {0x49fe40: "SET_DIPLO", 0x49ff10: "SET_LORD",
           0x49fd60: "GET_DIPLO", 0x49fe70: "GET_LORD",
           0x49fd80: "LOOKUP"}

def find_targets():
    hits = []
    i = 0
    while i + 5 <= len(code):
        if code[i] == 0xe8:
            import struct
            rel = struct.unpack("<i", code[i+1:i+5])[0]
            dst = (START + i + 5 + rel) & 0xffffffff
            if dst in TARGETS:
                hits.append((START + i, dst, TARGETS[dst]))
        i += 1
    return hits

hits = find_targets()
print(f"[*] 结算区域 0x{START:x}-0x{END:x} 内 setter/getter 调用: {len(hits)} 处\n")
for va, dst, tag in hits:
    print(f"0x{va:x}: call 0x{dst:x} [{tag}]")
