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
# 全二进制线性反汇编一次，过滤出引用 0x516638 的"写内存"指令，并 dump 渲染器 + 调用者
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', "rb").read()
BASE = 0x400000
N = len(MEM)
cs = Cs(CS_ARCH_X86, CS_MODE_32)
cs.detail = True

def disasm_all():
    instrs = []
    off = 0
    while off + 1 < N:
        md = cs.disasm(MEM[off:off+16], BASE + off)
        done = False
        for ins in md:
            instrs.append(ins)
            off += ins.size
            done = True
            break
        if not done:
            off += 1
    return instrs

print("disassembling full image (this may take a few seconds)...")
INS = disasm_all()
print(f"total instructions: {len(INS)}")

TARGET = 0x516638
writes = []
for ins in INS:
    t = ins.op_str
    if "0x516638" in t:
        # write: op_str like "byte ptr [0x516638], al"  -> first operand ends with "]"
        if "," in t and t.split(",")[0].strip().endswith("0x516638]"):
            writes.append(ins)

print(f"\n==== [A] 0x516638 WRITE references: {len(writes)} ====")
for ins in writes:
    print(f"  {ins.address:#010x}  {ins.mnemonic} {ins.op_str}")

# 渲染器
def dump(addr, n=200, tag=""):
    print(f"\n==== {tag} @ {addr:#010x} ====")
    off = addr - BASE
    md = cs.disasm(MEM[off:off+2200], addr)
    c = 0
    for ins in md:
        print(f"  {ins.address:#010x}  {ins.mnemonic} {ins.op_str}")
        c += 1
        if c >= n:
            break

# 调用者
def callers(callee):
    res = []
    for ins in INS:
        if ins.mnemonic == "call" and ins.op_str.strip() == f"0x{callee:X}":
            res.append(ins.address)
    return res

rd = callers(0x4e87e0)
print(f"\n==== [B] callers of renderer 0x4e87e0: {len(rd)} ====")
for c in rd:
    print(f"  {c:#010x}")

# dump 渲染器开头
dump(0x4e87e0, 90, "RENDERER 0x4e87e0")
