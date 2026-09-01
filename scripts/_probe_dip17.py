# -*- coding: utf-8 -*-
"""
_probe_dip17.py —
  A) 反汇编 0x4b9228（工作完了结算主函数）
  B) 全区扫描指向 0x4b9300..0x4b9800 的连续 dword 跳表
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


def dis(va, maxb=0x500, maxins=150):
    o = va - BASE
    out = []
    for ins in md.disasm(MEM[o:o + maxb], va):
        out.append(f"  {ins.address:#x}  {ins.mnemonic:<8} {ins.op_str}")
        if len(out) >= maxins or ins.mnemonic == "ret":
            break
    return "\n".join(out)


print("=" * 78)
print("### A) 0x4b9228")
print("=" * 78)
print(dis(0x4B9228, 0x500, 150))

print()
print("=" * 78)
print("### B) 跳表扫描 (0x4b9100..0x4b9f00, 目标 0x4b9300..0x4b9800)")
print("=" * 78)
start = 0x4B9100 - BASE
end = 0x4B9F00 - BASE
run = []
for i in range(start, end - 4, 4):
    v = struct.unpack("<I", MEM[i:i + 4])[0]
    if 0x4B9300 <= v <= 0x4B9800:
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
