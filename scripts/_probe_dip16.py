# -*- coding: utf-8 -*-
"""
_probe_dip16.py — 反汇编 0x4b91d0（工作结算主分派）+ 找其跳表
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

import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
MEM = open(MEM_PATH, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

o = 0x4B91D0 - BASE
print("=" * 78)
print("### 0x4b91d0 全文")
print("=" * 78)
n = 0
for ins in md.disasm(MEM[o:o + 0x400], 0x4B91D0):
    print(f"  {ins.address:#x}  {ins.mnemonic:<8} {ins.op_str}")
    n += 1
    if n >= 90:
        print("  ...")
        break
    if ins.mnemonic == "ret":
        break

print()
print("=" * 78)
print("### 扫描 0x4b9200..0x4b94ac 内指向 0x4b9300..0x4b9d00 的连续 dword 跳表")
print("=" * 78)
start = 0x4B9200 - BASE
end = 0x4B94AC - BASE
run = []
for i in range(start, end - 4, 4):
    v = struct.unpack("<I", MEM[i:i + 4])[0]
    if 0x4B9300 <= v <= 0x4B9D00:
        run.append((BASE + i, v))
segs = []
for x in run:
    if segs and x[0] - segs[-1][-1][0] == 4:
        segs[-1].append(x)
    else:
        segs.append([x])
for seg in segs:
    if len(seg) < 3:
        continue
    print(f"\n  --- 表段 {seg[0][0]:#x}  {len(seg)} 项 ---")
    for i, (a, v) in enumerate(seg):
        print(f"    [{i:2}] {a:#x} -> {v:#x}")
