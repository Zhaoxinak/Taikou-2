# -*- coding: utf-8 -*-
"""① 0x4ebcd0 语义  ② -12 通则把 BSDATA @44..@47 映射到 +0x20..+0x23。"""
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

from collections import Counter
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = _ROOT + '/scripts/_unpacked_mem.bin'
BSD = _ROOT + '/Taikou2 Original/BSDATA1.TR2'
BASE = 0x400000
mem = open(MEM, "rb").read()
b1 = open(BSD, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
REC, N = 59, 700

print("=" * 80)
print("A. 0x4ebcd0 语义")
print("=" * 80)
o = 0x4EBCD0 - BASE
for ins in md.disasm(mem[o:o + 48], 0x4EBCD0):
    print(f"  {ins.address:08x}  {ins.mnemonic:<8} {ins.op_str}")
    if ins.mnemonic == "ret":
        break

print("\n" + "=" * 80)
print("B. BSDATA @44..@47 实测 (对应实体 +0x20..+0x23, -12 通则)")
print("=" * 80)
for off, ent in ((44, 0x20), (45, 0x21), (46, 0x22), (47, 0x23)):
    v = [b1[REC * i + off] for i in range(N)]
    c = Counter(v)
    print(f"\n  @{off} → +{ent:#04x}: min={min(v)} max={max(v)} uniq={len(c)}")
    print(f"      top8={c.most_common(8)}")
    if off == 44:
        eq = sum(1 for i in range(N) if b1[REC * i + 44] == b1[REC * i + 45])
        print(f"      @44 == @45 : {eq}/700")
    if off == 47:
        print(f"      恒 50? {all(x == 50 for x in v)}")

print("\n" + "=" * 80)
print("C. 与 setter 钳制/常量比对")
print("=" * 80)
print("  +0x20 setter 0x49a650: cmp 0x64 (100)   ← @44 体力上限 范围?")
v44 = [b1[REC * i + 44] for i in range(N)]
print(f"      @44 全部 ≤100? {all(x <= 100 for x in v44)}  (min={min(v44)} max={max(v44)})")
v45 = [b1[REC * i + 45] for i in range(N)]
print(f"  +0x21 setter 0x49a630: 无钳制, 且初始化 = +0x20 / 100")
print(f"      @45 全部 ≤100? {all(x <= 100 for x in v45)}  (min={min(v45)} max={max(v45)})")
v46 = [b1[REC * i + 46] for i in range(N)]
print(f"  +0x22 setter 0x49a670: cmp 0x64 (100)   ← @46 体力消耗 uniq=16 (0/10/..100)?")
print(f"      @46 全部 %10==0? {all(x % 10 == 0 for x in v46)}  ≤100? {all(x <= 100 for x in v46)}")
v47 = [b1[REC * i + 47] for i in range(N)]
print(f"  +0x23 setter 0x49a690: 常量 0x32(50)/0x50(80)/0x64(100) ← @47 野心恒 50?")
print(f"      @47 分布 top5={Counter(v47).most_common(5)}")

print("\n" + "=" * 80)
print("D. -12 通则第四组验证汇总")
print("=" * 80)
pairs = [(22, 0x0a, "统御力"), (23, 0x0b, "武力"), (24, 0x0c, "内政力"),
         (25, 0x0d, "外交力"), (26, 0x0e, "魅力"),
         (27, 0x0f, "技能0-3"), (28, 0x10, "技能4-7"), (29, 0x11, "技能8-9"),
         (39, 0x1b, "生年"), (44, 0x20, "体力上限"), (45, 0x21, "体力(现役)"),
         (46, 0x22, "体力消耗"), (47, 0x23, "野心")]
allok = True
for bsd, ent, nm in pairs:
    ok = (bsd - 12) == ent
    allok &= ok
    print(f"    @{bsd:<3} → +{ent:#04x}  ({bsd} - 12 = {bsd-12} = {ent})  {'OK' if ok else 'NG'}  {nm}")
print(f"\n  全部成立? {allok}")
