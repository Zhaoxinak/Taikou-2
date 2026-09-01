# -*- coding: utf-8 -*-
"""
_probe_dip2.py — 外交结算核心追查
  A) 完整反汇编 0x4c5699（外交/谋略/情报 工作结算）
  B) 反汇编 0x4c5d00（0x4c582d 处 push [0x525ea4]; call 0x4c5d00）
  C) 反汇编 0x4c4270（选目标国）确认返回值语义
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

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
MEM = open(MEM_PATH, "rb").read()
SZ = len(MEM)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def va2off(va):
    return va - BASE


def dis(va, maxins=400, stops=("ret",)):
    o = va2off(va)
    out = []
    n = 0
    for ins in md.disasm(MEM[o:o + maxins * 8], va):
        out.append(f"  {ins.address:#x}  {ins.mnemonic:<8} {ins.op_str}")
        n += 1
        if n >= maxins:
            break
        if ins.mnemonic in stops:
            break
    return "\n".join(out)


def section(title):
    print("\n" + "=" * 78)
    print("### " + title)
    print("=" * 78)


section("B) 0x4c5d00  —— 疑似外交结算/成功率核心（参数 = [0x525ea4]）")
print(dis(0x4C5D00, maxins=300))

section("C) 0x4c4270  —— 选目标国（确认返回语义）")
print(dis(0x4C4270, maxins=200))

section("A) 0x4c5699  —— 外交/谋略/情报 工作结算（完整）")
# 不因 ret 提前停：用较大上限
o = va2off(0x4C5699)
n = 0
for ins in md.disasm(MEM[o:o + 0x900], 0x4C5699):
    print(f"  {ins.address:#x}  {ins.mnemonic:<8} {ins.op_str}")
    n += 1
    if n >= 420:
        print("  ... (truncated)")
        break
    if ins.mnemonic == "ret" and ins.address > 0x4C5900:
        break
