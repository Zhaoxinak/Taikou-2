# -*- coding: utf-8 -*-
"""位域分解 @39/@40/@41 并用简体史实名标定剧本年。"""
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
import statistics as st

B1 = _ROOT + '/Taikou2 Original/BSDATA1.TR2'
b1 = open(B1, "rb").read()
REC, N = 59, 700


def name(i):
    o = REC * i
    return (b1[o:o + 7].split(b"\x00")[0].decode("gbk", "replace") +
            b1[o + 7:o + 13].split(b"\x00")[0].decode("gbk", "replace"))


def f(i, off):
    return b1[REC * i + off]


idx = {name(i): i for i in range(N)}

print("=" * 78)
print("A. @40 位域分解候选")
print("=" * 78)
v40 = [f(i, 40) for i in range(N)]
for shift, mask_n in ((5, 32), (4, 16), (3, 8), (6, 64)):
    hi = Counter(v >> shift for v in v40)
    lo = Counter(v & (mask_n - 1) for v in v40)
    print(f"  >>{shift} (高位, /{mask_n}): {sorted(hi.items())[:10]}")
    print(f"  &{mask_n-1:<3} (低位)      : {sorted(lo.items())[:12]}")

print("\n  → 选 >>5/&31 细看:")
hi = Counter(v >> 5 for v in v40)
lo = Counter(v & 31 for v in v40)
print(f"    高位(@40>>5): {sorted(hi.items())}")
print(f"    低位(@40&31): {sorted(lo.items())}")

print("\n" + "=" * 78)
print("B. @39 位域分解")
print("=" * 78)
v39 = [f(i, 39) for i in range(N)]
b7 = Counter((v >> 7) & 1 for v in v39)
lo7 = Counter(v & 0x7F for v in v39)
print(f"  bit7: {dict(b7)}")
print(f"  &0x7f: min={min(x for x in lo7)} max={max(x for x in lo7)} uniq={len(lo7)}")
print(f"  &0x7f top12: {lo7.most_common(12)}")

print("\n" + "=" * 78)
print("C. @41 (544 条 =255 哨兵)")
print("=" * 78)
v41 = [f(i, 41) for i in range(N)]
print(f"  =255: {sum(1 for v in v41 if v == 255)}/700")
other = [v for v in v41 if v != 255]
print(f"  其余 {len(other)} 条: min={min(other)} max={max(other)}")

print("\n" + "=" * 78)
print("D. 简体史实名标定 (剧本年 = 生年 + 候选年龄字段)")
print("=" * 78)
KNOWN = [
    ("织田信长", 1534), ("武田信玄", 1521), ("上杉谦信", 1530),
    ("德川家康", 1543), ("毛利元就", 1497), ("今川义元", 1519),
    ("斋藤道三", 1494), ("丰臣秀吉", 1537), ("明智光秀", 1528),
    ("服部半藏", 1542), ("伊达政宗", 1567), ("真田幸村", 1567),
    ("石田三成", 1560), ("柴田胜家", 1522), ("丹羽长秀", 1535),
    ("前田利家", 1539), ("蜂须贺小六", 1526), ("今川氏真", 1538),
    ("武田胜赖", 1546), ("北条氏政", 1538), ("上杉景胜", 1556),
    ("黑田官兵卫", 1546), ("竹中半兵卫", 1544), ("浅井长政", 1545),
]
found = []
for nm, by in KNOWN:
    i = idx.get(nm)
    if i is None:
        continue
    x39, x40, x41, x43, x58 = f(i, 39), f(i, 40), f(i, 41), f(i, 43), f(i, 58)
    found.append((nm, by, x39, x40, x41, x43, x58,
                  x39 & 0x7F, x40 >> 5, x40 & 31))
print(f"  命中 {len(found)}/{len(KNOWN)}")
print(f"\n  {'人物':<12}{'生年':>6}{'@39':>5}{'@40':>5}{'@41':>5}{'@43':>5}{'@58':>5}"
      f"{'@39&7f':>8}{'@40>>5':>8}{'@40&31':>8}{'生+&7f':>8}{'生+>>5':>8}{'生+&31':>8}")
for r in found:
    print(f"  {r[0]:<12}{r[1]:>6}{r[2]:>5}{r[3]:>5}{r[4]:>5}{r[5]:>5}{r[6]:>5}"
          f"{r[7]:>8}{r[8]:>8}{r[9]:>8}{r[1]+r[7]:>8}{r[1]+r[8]:>8}{r[1]+r[9]:>8}")

for lbl, k in (("@39&0x7f", 7), ("@40>>5", 8), ("@40&31", 9)):
    ys = [r[1] + r[k] for r in found]
    c = Counter(ys)
    print(f"\n  按 {lbl} 推定剧本年: top5={c.most_common(5)}  中位={int(st.median(ys))}")

print("\n" + "=" * 78)
print("E. 全 700 条: 若 @39&0x7f 是年龄, 分布是否合理")
print("=" * 78)
ages = [f(i, 39) & 0x7F for i in range(N)]
print(f"  min={min(ages)} max={max(ages)} 均值={st.mean(ages):.1f} 中位={int(st.median(ages))}")
print(f"  直方图(5岁一档): {sorted(Counter(a//5*5 for a in ages).items())}")
