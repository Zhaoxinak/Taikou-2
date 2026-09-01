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
# 字节级 xref 扫描器：找某绝对地址在数据/指令中的引用，并解码指令区分 读/写/取地址。
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import *

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()

def off(v): return v - BASE

def find_imm(va):
    pat = struct.pack('<I', va & 0xffffffff)
    out = []
    i = 0
    while True:
        i = MEM.find(pat, i)
        if i < 0:
            break
        out.append(BASE + i)
        i += 1
    return out

def classify(va):
    """滑窗反汇编，找包含该 4 字节立即数的指令，并分类其对 va 的操作。"""
    mdl = Cs(CS_ARCH_X86, CS_MODE_32); mdl.detail = True
    start = va - 15
    window = MEM[off(start):off(va)+8]
    for ins in mdl.disasm(window, start):
        # 该指令必须“覆盖”立即数所在的 4 字节区间
        if not (ins.address <= va and ins.address + ins.size >= va + 4):
            continue
        for op in ins.operands:
            if op.type == CS_OP_MEM:
                if op.mem.disp == (va - BASE) and op.mem.base == 0 and op.mem.index == 0:
                    if ins.mnemonic == 'lea':
                        return 'LEA', ins
                    if len(ins.operands) >= 2:
                        if ins.operands[0].type == CS_OP_MEM:
                            return 'WRITE', ins
                        if ins.operands[1].type == CS_OP_MEM:
                            return 'READ', ins
                    return 'MEM', ins
            if op.type == CS_OP_IMM and (op.imm & 0xffffffff) == va:
                return 'IMM', ins
    return 'NONE', None

if __name__ == '__main__':
    import sys
    targets = [int(x, 16) for x in sys.argv[1:]] if len(sys.argv) > 1 else [0x525ea4, 0x5179b8]
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
    for tgt in targets:
        hits = find_imm(tgt)
        print(f"=== 0x{tgt:08x}: {len(hits)} hits ===")
        buckets = {'WRITE': [], 'READ': [], 'LEA': [], 'MEM': [], 'IMM': [], 'NONE': []}
        for h in hits:
            kind, ins = classify(h)
            buckets.setdefault(kind, []).append((h, ins))
        for kind in ('WRITE', 'READ', 'LEA', 'MEM', 'IMM', 'NONE'):
            lst = buckets[kind]
            if not lst:
                continue
            print(f"  -- {kind} ({len(lst)}) --")
            for h, ins in lst[:40]:
                s = f"    @{h:#010x}  {ins.address:08x}  {ins.bytes.hex():18s} {ins.mnemonic} {ins.op_str}" if ins else f"    @{h:#010x}  (no decode)"
                print(s)
