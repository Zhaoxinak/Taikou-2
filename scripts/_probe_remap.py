# -*- coding: utf-8 -*-
"""-12 通则逐字段实测: 实体[i] = BSDATA[i+12] ? 用 setter 钳制/哨兵 vs 实测值域比对。"""
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
import struct

BSD1 = _ROOT + '/Taikou2 Original/BSDATA1.TR2'
BSD2 = _ROOT + '/Taikou2 Original/BSDATA2.TR2'
b1 = open(BSD1, "rb").read()
b2 = open(BSD2, "rb").read()
REC, N = 59, 700
ENT = 47           # 武将实体 stride

print("=" * 84)
print("A. 结构性前提")
print("=" * 84)
print(f"  BSDATA 记录 = {REC} 字节; 武将实体 stride = {ENT} 字节; 差 = {REC - ENT}")
print(f"  ⇒ 主张: 实体 = BSDATA 记录去掉前 {REC-ENT} 字节(姓名区 @0..@11), 即 entity[i] = bsdata[i+{REC-ENT}]")

print("\n" + "=" * 84)
print("B. 姓名区是否正好 12 字节")
print("=" * 84)
# @0..@6 姓, @7..@12 名(6B); 取 @0..@11 看是否全为姓名/填充
c12 = Counter()
for i in range(N):
    o = REC * i
    seg = b1[o:o + 12]
    # 是否以 00 收尾 (GBK 姓名以 0 结尾)
    c12[seg[-1] == 0] += 1
print(f"  @0..@11 末字节为 0x00 的比例: {c12}")
c13 = Counter()
for i in range(N):
    o = REC * i
    c13[b1[o + 12]] += 1
print(f"  @12 取值分布 top5: {c13.most_common(5)}   (若为名的末字节则多为 0)")
c14 = Counter(b1[REC * i + 13] for i in range(N))
print(f"  @13 取值分布: {c14.most_common(4)}   (spec 记 @13 恒 0x00)")

print("\n" + "=" * 84)
print("C. 实体 setter 钳制/哨兵 表")
print("=" * 84)
# 由续132/133/134 的方法表整理: 实体偏移 -> (钳制上限, 备注)
SETTERS = {
    0x0A: (100, "统御力"), 0x0B: (100, "武力"), 0x0C: (100, "内政力"),
    0x0D: (100, "外交力"), 0x0E: (100, "魅力"),
    0x20: (100, "体力上限"), 0x21: (None, "体力(现役)"),
    0x22: (100, "体力消耗"), 0x23: (100, "野心"),
    0x26: (60000, "功勲(word)"), 0x28: (200, "?"), 0x29: (100, "忠诚"),
}
print(f"  {'实体偏移':<10}{'钳制':<10}{'语义':<14}{'BSDATA偏移':<12}{'实测范围':<16}{'判定'}")
rows = []
for off, (cap, nm) in sorted(SETTERS.items()):
    bsd_off = off + 12
    v = [b1[REC * i + bsd_off] for i in range(N)]
    if cap is None:
        verdict = "n/a"
    else:
        verdict = "OK" if max(v) <= cap else f"越界 max={max(v)}>{cap}"
    rows.append((off, cap, nm, bsd_off, min(v), max(v), verdict))
    print(f"  +{off:#04x}     {str(cap):<10}{nm:<14}@{bsd_off:<11}"
          f"{f'{min(v)}..{max(v)}':<16}{verdict}")

print("\n" + "=" * 84)
print("D. word 字段 (@50..@51 → +0x26..+0x27 ?) 检查")
print("=" * 84)
# @50..@51 = 信赖 trust word (37+118=155 个 0, max=65280)
w = [struct.unpack_from("<H", b1, REC * i + 50)[0] for i in range(N)]
print(f"  BSDATA @50..@51 (word): min={min(w)} max={max(w)} uniq={len(set(w))}")
print(f"  若为实体 +0x26 (功勲, 钳 60000): 越界数 = {sum(1 for x in w if x > 60000)}/700")
# 对比: 若映射到 +0x24..+0x25 (shift 12 => 50-12=38=0x26) 同上
for shift in (10, 11, 12, 13, 14):
    e = 50 - shift
    print(f"    shift={shift}: @50 → +{e:#04x} ({e})")

print("\n" + "=" * 84)
print("E. 后段 @54..@58 的候选实体落点（用值域反推最可能的偏移）")
print("=" * 84)
for bsd_off in range(48, 59):
    v = [b1[REC * i + bsd_off] for i in range(N)]
    uniq = len(set(v))
    print(f"  @{bsd_off}: min={min(v):<5} max={max(v):<5} uniq={uniq:<5} "
          f"top3={Counter(v).most_common(3)}")

print("\n" + "=" * 84)
print("F. 关键交叉: @31 / @49 (现城) 是否都映射到已知的实体双写对 +0x13/+0x25")
print("=" * 84)
eq3149 = sum(1 for i in range(N) if b1[REC * i + 31] == b1[REC * i + 49])
print(f"  @31 == @49 : {eq3149}/700")
print(f"  -12 通则: @31 → +{31-12:#04x}  @49 → +{49-12:#04x}  (续114 实测 +0x13 是 +0x25 的副本 ⇒ 双写对 ✓)")
print(f"  现城哨兵 255 出现次数: @31={sum(1 for i in range(N) if b1[REC*i+31]==255)}, "
      f"@49={sum(1 for i in range(N) if b1[REC*i+49]==255)}")
print(f"  +0x25 setter (0x49a760) 调用常量含 0xff(255) ⇒ 与现城哨兵一致 ✓")

print("\n" + "=" * 84)
print("G. 现城 id 值域 vs 城数 200")
print("=" * 84)
v31 = [b1[REC * i + 31] for i in range(N)]
print(f"  @31 max={max(v31)}  城表 200 条 (0..199 + 255 哨兵)")
print(f"  >199 且 !=255 的条数: {sum(1 for x in v31 if x > 199 and x != 255)}")
