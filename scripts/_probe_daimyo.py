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
# 从已知入口点反汇编（避免线性漂移）：大名(7) 调用点、領地表、标志置位点
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', "rb").read()
BASE = 0x400000
N = len(MEM)
cs = Cs(CS_ARCH_X86, CS_MODE_32)
cs.detail = True

def dump(addr, bytes_, tag=""):
    print(f"\n==== {tag} @ {addr:#010x} ({bytes_}B) ====")
    off = addr - BASE
    md = cs.disasm(MEM[off:off+bytes_], addr)
    for ins in md:
        print(f"  {ins.address:#010x}  {ins.mnemonic} {ins.op_str}")

def read_table(addr, stride, count, fmt):
    print(f"\n==== TABLE @ {addr:#010x} stride={stride} count={count} ====")
    off = addr - BASE
    for i in range(count):
        base = off + i*stride
        vals = struct.unpack_from(fmt, MEM, base)
        print(f"  [{i:2d}] " + " ".join(f"{v:#x}" if isinstance(v,int) else str(v) for v in vals))

import struct
# 1) 大名 set_rank(7) 调用点：0x4c2d9a（另三个已知：0x40fedf/0x416ca1/0x4a4059）
dump(0x4c2d70, 120, "CALLER 0x4c2d9a set_rank(7)")
dump(0x416c80, 130, "CALLER 0x416ca1 set_rank(7) (territory)")
dump(0x4a4030, 80,  "CALLER 0x4a4059 set_rank(7) (succession)")
# 2) 領地表 0x5179b8 stride 8
read_table(0x5179b8, 8, 16, "<II")
# 3) 标志置位点
dump(0x47e850, 90, "FLAG setter 0x47e879 push 0x516638")
dump(0x4cbd90, 90, "FLAG add 0x4cbdbf [ecx+0x516638]")
# 4) 0x5179b8 周边：看它是什么表（城数→？）
dump(0x5179a0, 60, "before 0x5179b8")
