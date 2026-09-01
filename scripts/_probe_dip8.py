# -*- coding: utf-8 -*-
"""
_probe_dip8.py — 定位「改关系值」的写入端
  A) 0x49fd80 (关系记录查找) 的全部 e8 调用方
  B) 对每个调用方函数, 检查调用后是否【写】返回的字节 -> 即关系变更点
  C) 反汇编命中的写入函数全文
"""
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

import struct, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
MEM = open(MEM_PATH, "rb").read()
SZ = len(MEM)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def dis(va, maxins=200):
    o = va - BASE
    out = []
    for ins in md.disasm(MEM[o:o + maxins * 8], va):
        out.append((ins.address, ins.mnemonic, ins.op_str, ins.size))
        if len(out) >= maxins or ins.mnemonic == "ret":
            break
    return out


def func_start(va):
    o = va - BASE
    lim = max(0, o - 0x800)
    i = o
    while i > lim:
        b = MEM[i]
        if b == 0xC3:
            return BASE + i + 1
        if b == 0xC2 and i + 2 < SZ:
            return BASE + i + 3
        i -= 1
    return BASE + lim


def e8_callers(va, lo=0x401000, hi=0x520000):
    out = []
    i = lo - BASE
    end = hi - BASE
    while i < end - 5:
        if MEM[i] == 0xE8:
            rel = struct.unpack("<i", MEM[i + 1:i + 5])[0]
            if BASE + i + 5 + rel == va:
                out.append(BASE + i)
        i += 1
    return out


# 判断指令是否写内存（目标在第一个操作数且是 byte ptr [reg] / [reg+disp]）
WRITE_MN = {"mov", "or", "and", "add", "sub", "xor", "inc", "dec", "shl",
            "shr", "sar", "imul", "adc", "sbb", "not", "neg"}


def is_byte_write(mn, op_str):
    if mn not in WRITE_MN:
        return False
    first = op_str.split(",", 1)[0].strip()
    return bool(re.match(r"^(byte|word|dword)?\s*ptr\s*\[", first)) or \
        bool(re.match(r"^byte\s+ptr", first))


TARGET = 0x49FD80
callers = e8_callers(TARGET)
print("=" * 78)
print(f"### A) 0x49fd80 的 e8 调用方: {len(callers)} 处")
print("=" * 78)
print("  " + ", ".join(hex(c) for c in callers))

print()
print("=" * 78)
print("### B) 逐个检查调用后是否写入返回字节")
print("=" * 78)
writers = []
for c in callers:
    fs = func_start(c)
    ins_list = dis(fs, 400)
    # 找调用点位置
    idx = next((i for i, x in enumerate(ins_list) if x[0] == c), None)
    if idx is None:
        continue
    # 向后 25 条指令内是否出现字节写
    hits = []
    for j in range(idx, min(idx + 25, len(ins_list))):
        a, mn, ops, sz = ins_list[j]
        if is_byte_write(mn, ops):
            hits.append((a, mn, ops))
    tag = "WRITE" if hits else "read "
    print(f"\n  [{tag}] call@{c:#x}  func={fs:#x}")
    for a, mn, ops in hits[:6]:
        print(f"        {a:#x}  {mn:<6} {ops}")
    if hits:
        writers.append(fs)

print()
print("=" * 78)
print(f"### C) 关系写入函数全文 ({len(writers)} 个)")
print("=" * 78)
for w in sorted(set(writers)):
    print(f"\n---------- {w:#x} ----------")
    for a, mn, ops, sz in dis(w, 220):
        print(f"  {a:#x}  {mn:<8} {ops}")
