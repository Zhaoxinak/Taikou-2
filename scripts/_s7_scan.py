# -*- coding: utf-8 -*-
"""S7 @0x516a28 (200x16B 每城运行时表) 写入点静态搜索。
搜索字面值 0x516a28 在全映像中的所有出现，反汇编上下文，找 setter/直接写。"""
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
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', "rb").read()
S7_BASE = 0x516a28
S7_HI = S7_BASE + 200 * 16  # 0x5173e8
TARGET = struct.pack("<I", S7_BASE)

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

# 1) 找所有字面值 0x516a28 的文件偏移
hits = []
start = 0
while True:
    i = MEM.find(TARGET, start)
    if i < 0:
        break
    hits.append(i)
    start = i + 1

print("字面值 0x516a28 出现次数: %d" % len(hits))


def ctx(va, before=0x18, after=0x30):
    code = MEM[va - BASE - before: va - BASE + after]
    out = []
    for ins in md.disasm(code, va - before):
        out.append(ins)
        if len(out) > 24:
            break
    return out


# 2) 对每个命中，反汇编上下文，标注引用性质
for off in hits:
    va = BASE + off
    insts = ctx(va)
    ref_type = "?"
    # 看命中地址本身的指令（其在反汇编流中的索引）
    hit_ins = None
    for ins in insts:
        if ins.address <= va < ins.address + max(1, ins.size):
            hit_ins = ins
            break
    if hit_ins is None:
        continue
    s = hit_ins.op_str
    if "0x516a28" in s:
        ref_type = "IMM引用"
    elif hit_ins.mnemonic == "mov" and "0x516a28" in s:
        ref_type = "mov 基址"
    note = ""
    # 判断是否附近有 call（疑似 setter 派发）
    callees = [ins for ins in insts if ins.mnemonic == "call"]
    if callees:
        note = " calls: " + ", ".join("0x%06x" % c.operands[0].imm for c in callees if c.operands)
    print("\n=== VA 0x%06x (file 0x%x) %s%s" % (va, off, ref_type, note))
    for ins in insts:
        mark = " >>" if ins.address == va else "   "
        print("%s0x%06x %-8s %s" % (mark, ins.address, ins.mnemonic, ins.op_str))
