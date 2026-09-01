# -*- coding: utf-8 -*-
"""以已知生年为锚, 系统检验 @40/@41/@43/@58 的候选语义。"""
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


def nm(i):
    o = REC * i
    return (b1[o:o + 7].split(b"\x00")[0].decode("gbk", "replace") +
            b1[o + 7:o + 13].split(b"\x00")[0].decode("gbk", "replace"))


def F(i, off):
    return b1[REC * i + off]


idx = {nm(i): i for i in range(N)}

# (名, 生年, 死亡年)
KNOWN = [
    ("织田信长", 1534, 1582), ("武田信玄", 1521, 1573), ("上杉谦信", 1530, 1578),
    ("德川家康", 1542, 1616), ("毛利元就", 1497, 1571), ("明智光秀", 1528, 1582),
    ("服部半藏", 1542, 1596), ("伊达政宗", 1567, 1636), ("真田幸村", 1567, 1615),
    ("石田三成", 1560, 1600), ("柴田胜家", 1521, 1583), ("丹羽长秀", 1535, 1585),
    ("前田利家", 1538, 1599), ("蜂须贺小六", 1526, 1586), ("今川氏真", 1538, 1615),
    ("武田胜赖", 1546, 1582), ("北条氏政", 1538, 1590), ("上杉景胜", 1555, 1623),
    ("黑田官兵卫", 1546, 1604), ("竹中半兵卫", 1544, 1579), ("浅井长政", 1545, 1573),
]
rows = []
for n_, by, dy in KNOWN:
    i = idx.get(n_)
    if i is None:
        continue
    rows.append((n_, by, dy, dy - by, F(i, 39) & 0x7F, F(i, 40), F(i, 41),
                 F(i, 43), F(i, 58), (F(i, 39) >> 7) & 1))

print("=" * 92)
print("A. 已知人物全字段 (生年 = 1490 + @39&0x7f 已验证 21/21)")
print("=" * 92)
print(f"  {'人物':<12}{'生':>5}{'死':>5}{'寿':>4}{'@39&7f':>8}{'b7':>3}"
      f"{'@40':>5}{'@40>>5':>7}{'@40&31':>7}{'@41':>5}{'@43':>5}{'@58':>5}{'@58>>4':>7}")
for r in rows:
    print(f"  {r[0]:<12}{r[1]:>5}{r[2]:>5}{r[3]:>4}{r[4]:>8}{r[9]:>3}"
          f"{r[5]:>5}{r[5]>>5:>7}{r[5]&31:>7}{r[6]:>5}{r[7]:>5}{r[8]:>5}{r[8]>>4:>7}")


def corr(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    dx = sum((a - mx) ** 2 for a in xs) ** .5
    dy = sum((b - my) ** 2 for b in ys) ** .5
    return num / (dx * dy) if dx and dy else 0.0


by = [r[1] for r in rows]
dy = [r[2] for r in rows]
life = [r[3] for r in rows]
print("\n" + "=" * 92)
print("B. 相关性 (与生年/死亡年/寿命)")
print("=" * 92)
cands = {
    "@40": [r[5] for r in rows], "@40>>5": [r[5] >> 5 for r in rows],
    "@40&31": [r[5] & 31 for r in rows],
    "@41(非255)": [r[6] for r in rows if r[6] != 255],
    "@43": [r[7] for r in rows], "@58": [r[8] for r in rows],
    "@58>>4": [r[8] >> 4 for r in rows],
    "@39 bit7": [r[9] for r in rows],
}
for lbl, v in cands.items():
    xs = by[:len(v)]
    ys = dy[:len(v)]
    ls = life[:len(v)]
    print(f"  {lbl:<12} n={len(v):<3} corr(生)={corr(xs, v):+.3f}  "
          f"corr(死)={corr(ys, v):+.3f}  corr(寿)={corr(ls, v):+.3f}")

print("\n" + "=" * 92)
print("C. @40 与 生年 的代数关系试探 (全 700 条)")
print("=" * 92)
birth = [1490 + (F(i, 39) & 0x7F) for i in range(N)]
v40 = [F(i, 40) for i in range(N)]
print(f"  corr(生年, @40)      = {corr(birth, v40):+.3f}")
print(f"  corr(生年, @40>>5)   = {corr(birth, [v >> 5 for v in v40]):+.3f}")
print(f"  corr(生年, @40&31)   = {corr(birth, [v & 31 for v in v40]):+.3f}")
# 试 (生年 - k) mod 32 == @40&31 ?
for k in range(1540, 1580):
    hit = sum(1 for i in range(N) if (birth[i] - k) % 32 == (v40[i] & 31))
    if hit > 250:
        print(f"  (生年-{k}) mod 32 == @40&31 : {hit}/700")
# 试 生年 - 1490 - @40 关系
for k in range(0, 200, 1):
    hit = sum(1 for i in range(N) if (birth[i] + k) % 32 == (v40[i] & 31))
    if hit > 300:
        print(f"  (生年+{k}) mod 32 == @40&31 : {hit}/700")
        break

print("\n" + "=" * 92)
print("D. @58 / @43 分组下的生年分布 (全 700)")
print("=" * 92)
g = {}
for i in range(N):
    g.setdefault(F(i, 58), []).append(birth[i])
for k in sorted(g):
    v = g[k]
    print(f"  @58={k:>3}(>>4={k>>4})  n={len(v):<4} 生年 均值={st.mean(v):7.1f} "
          f"中位={int(st.median(v))} 范围 {min(v)}..{max(v)}")
print()
g43 = {}
for i in range(N):
    g43.setdefault(F(i, 43) // 10 * 10, []).append(birth[i])
for k in sorted(g43):
    v = g43[k]
    print(f"  @43∈[{k},{k+9}]  n={len(v):<4} 生年 均值={st.mean(v):7.1f} 中位={int(st.median(v))}")
print(f"\n  corr(生年, @43) = {corr(birth, [F(i,43) for i in range(N)]):+.3f}")
print(f"  corr(生年, @58) = {corr(birth, [F(i,58) for i in range(N)]):+.3f}")
print(f"  corr(@43, @58)  = {corr([F(i,43) for i in range(N)], [F(i,58) for i in range(N)]):+.3f}")
