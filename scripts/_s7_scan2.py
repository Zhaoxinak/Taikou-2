# -*- coding: utf-8 -*-
"""S7 字段布局提取（用 capstone reg_name 取寄存器名，避免枚举值误判）。"""
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
TARGET = struct.pack("<I", S7_BASE)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def dis(va, n):
    return list(md.disasm(MEM[va - BASE: va - BASE + n], va))


def reg_n(ins, reg_id):
    return md.reg_name(reg_id) if reg_id else None


def find_hits():
    hits = []
    s = 0
    while True:
        i = MEM.find(TARGET, s)
        if i < 0:
            break
        hits.append(BASE + i)
        s = i + 1
    return hits


hits = find_hits()
reader_offsets = {}
setter_calls = set()

for va in hits:
    ctx = dis(va - 0x10, 0x210)
    s7reg = None
    for ins in ctx:
        if ins.address <= va < ins.address + max(1, ins.size):
            s7reg = reg_n(ins, ins.operands[0].reg)
            break
    if not s7reg:
        continue
    for ins in dis(va, 0x400):
        for op in ins.operands:
            if op.type == 3 and reg_n(ins, op.mem.base) == s7reg:
                disp = op.mem.disp & 0xff
                if 0 <= disp <= 15:
                    reader_offsets.setdefault(disp, []).append(
                        "%s@0x%x" % (ins.mnemonic, ins.address))
        if ins.mnemonic == "call":
            setter_calls.add(ins.operands[0].imm)

print("=== 读者函数对 S7 指针 [reg+0..15] 的访问 ===")
for off in sorted(reader_offsets):
    print("  +0x%02x : %s" % (off, reader_offsets[off][:8]))

print("\n=== 候选 setter（被传 ecx=&S7[城] 调用）===")
print("  ", [hex(t) for t in sorted(setter_calls)])

print("\n=== setter 内部对 ecx(this) 的 [ecx+disp] 写入 ===")
for tgt in sorted(setter_calls):
    writes = []
    for ins in dis(tgt, 0x140):
        if ins.mnemonic in ("mov", "add", "sub", "and", "or", "xor", "test"):
            for op in ins.operands:
                if op.type == 3 and reg_n(ins, op.mem.base) == "ecx":
                    disp = op.mem.disp & 0xff
                    if 0 <= disp <= 15:
                        writes.append("0x%x %s %s" % (ins.address, ins.mnemonic, ins.op_str))
    if writes:
        print("  %s :" % hex(tgt))
        for w in writes[:10]:
            print("      ", w)
