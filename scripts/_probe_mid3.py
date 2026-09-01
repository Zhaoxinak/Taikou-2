# -*- coding: utf-8 -*-
"""① 0x49ac80..0x49ae00 剩余入口(找 +0x1f setter) ② 身分名表 0x507778 stride7。"""
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

import re, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
mem = open(MEM, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)

print("=" * 86)
print("A. 0x49ac60 .. 0x49ae00")
print("=" * 86)
o = 0x49AC60 - BASE
for ins in md.disasm(mem[o:o + 0x1A0], 0x49AC60):
    print(f"  {ins.address:08x}  {ins.mnemonic:<8} {ins.op_str}")

print("\n" + "=" * 86)
print("B. 身分名表 0x507778 (stride 7) —— 由 0x49a920 `(word[+0x2c]>>8)&7` 索引")
print("=" * 86)
for i in range(10):
    va = 0x507778 + 7 * i
    raw = mem[va - BASE: va - BASE + 7]
    print(f"  [{i}] {va:#010x} {raw.hex()}  {raw.split(b'\\x00')[0].decode('gbk','replace')!r}")

print("\n  对照: 能力名表 0x507fc0 (stride 7)")
for i in range(5):
    va = 0x507FC0 + 7 * i
    raw = mem[va - BASE: va - BASE + 7]
    print(f"  [{i}] {va:#010x} {raw.hex()}  {raw.split(b'\\x00')[0].decode('gbk','replace')!r}")

print("\n" + "=" * 86)
print("C. 0x49a920 全文复核 (身分名 getter)")
print("=" * 86)
o = 0x49A920 - BASE
for ins in md.disasm(mem[o:o + 0x20], 0x49A920):
    print(f"  {ins.address:08x}  {ins.mnemonic:<8} {ins.op_str}")
    if ins.mnemonic == "ret":
        break
# 7*idx: lea eax,[ecx+ecx*2](3x)... 实际是 shl 3 - x = 7x
print("\n  eax = (idx*8) - idx = 7*idx  ⇒ 基址 0x507778, stride 7 ✓")
