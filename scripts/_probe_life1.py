# -*- coding: utf-8 -*-
"""BSDATA 生日/寿命组统计定位: @39/@40/@41/@43/@58。"""
from collections import Counter
import statistics as st

B1 = "F:/Games/Taikou 2/Taikou2 Original/BSDATA1.TR2"
B2 = "F:/Games/Taikou 2/Taikou2 Original/BSDATA2.TR2"
b1 = open(B1, "rb").read()
b2 = open(B2, "rb").read()
REC, N = 59, 700


def name(b, i):
    o = REC * i
    return (b[o:o + 7].split(b"\x00")[0].decode("gbk", "replace") +
            b[o + 7:o + 13].split(b"\x00")[0].decode("gbk", "replace"))


def f(b, i, off):
    return b[REC * i + off]


print("=" * 78)
print("A. 跨剧本差分 (哪些字段在 BSDATA1 vs BSDATA2 不同)")
print("=" * 78)
for off in range(59):
    diff = sum(1 for i in range(N) if f(b1, i, off) != f(b2, i, off))
    if diff:
        print(f"  @{off:<3} 不同 {diff}/700")

print("\n" + "=" * 78)
print("B. @40 跨剧本差值分布 (若为年龄, 差值应恒定 = 剧本年差)")
print("=" * 78)
d40 = Counter(f(b2, i, 40) - f(b1, i, 40) for i in range(N))
print(f"  @40 差值分布: {sorted(d40.items())}")
for off in (39, 41, 43, 58, 44, 45):
    d = Counter(f(b2, i, off) - f(b1, i, off) for i in range(N))
    print(f"  @{off} 差值分布: {sorted(d.items())[:8]}")

print("\n" + "=" * 78)
print("C. 用史实生年标定: 剧本年 = 生年 + @40(年龄)")
print("=" * 78)
KNOWN = [
    ("織田信長", 1534), ("武田信玄", 1521), ("上杉謙信", 1530),
    ("徳川家康", 1543), ("毛利元就", 1497), ("今川義元", 1519),
    ("斎藤道三", 1494), ("豊臣秀吉", 1537), ("明智光秀", 1528),
    ("千利休", 1522), ("服部半蔵", 1542), ("伊達政宗", 1567),
    ("真田幸村", 1567), ("石田三成", 1560), ("柴田勝家", 1522),
    ("丹羽長秀", 1535), ("前田利家", 1539), ("蜂須賀小六", 1526),
]
idx = {name(b1, i): i for i in range(N)}
rows = []
for nm, by in KNOWN:
    # 名字可能用简体/异体, 做模糊匹配
    hit = [i for n, i in idx.items() if n == nm]
    if not hit:
        cands = [n for n in idx if nm[0] in n]
        print(f"  {nm:<8} 未精确命中; 同首字候选: {cands[:5]}")
        continue
    i = hit[0]
    a1, a2 = f(b1, i, 40), f(b2, i, 40)
    rows.append((nm, by, a1, a2, by + a1, by + a2,
                 f(b1, i, 39), f(b1, i, 41), f(b1, i, 43), f(b1, i, 58)))
print(f"\n  {'人物':<10}{'生年':>6}{'@40(剧1)':>9}{'@40(剧2)':>9}"
      f"{'生+@40 剧1':>11}{'生+@40 剧2':>11}{'@39':>5}{'@41':>5}{'@43':>5}{'@58':>5}")
for r in rows:
    print(f"  {r[0]:<10}{r[1]:>6}{r[2]:>9}{r[3]:>9}{r[4]:>11}{r[5]:>11}"
          f"{r[6]:>5}{r[7]:>5}{r[8]:>5}{r[9]:>5}")
if rows:
    y1 = [r[4] for r in rows]
    y2 = [r[5] for r in rows]
    print(f"\n  剧本1 推定年: 中位 {int(st.median(y1))}  范围 {min(y1)}..{max(y1)}")
    print(f"  剧本2 推定年: 中位 {int(st.median(y2))}  范围 {min(y2)}..{max(y2)}")
    c1, c2 = Counter(y1).most_common(3), Counter(y2).most_common(3)
    print(f"  剧本1 top3: {c1}")
    print(f"  剧本2 top3: {c2}")

print("\n" + "=" * 78)
print("D. @39/@40/@41/@43/@58 单字段分布")
print("=" * 78)
for off in (39, 40, 41, 43, 58):
    v = [f(b1, i, off) for i in range(N)]
    c = Counter(v)
    print(f"  @{off}: min={min(v)} max={max(v)} uniq={len(c)}")
    print(f"        top10={c.most_common(10)}")

print("\n" + "=" * 78)
print("E. 相关性: @58 vs @40(年龄) / @43 / @39 / @41")
print("=" * 78)


def corr(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    dx = sum((a - mx) ** 2 for a in xs) ** .5
    dy = sum((b - my) ** 2 for b in ys) ** .5
    return num / (dx * dy) if dx and dy else 0.0


a40 = [f(b1, i, 40) for i in range(N)]
for off in (39, 41, 43, 58, 44, 45, 46):
    v = [f(b1, i, off) for i in range(N)]
    print(f"  corr(@40, @{off}) = {corr(a40, v):+.3f}")

print("\n  @58 分组下的 @40(年龄) 统计:")
g = {}
for i in range(N):
    g.setdefault(f(b1, i, 58), []).append(f(b1, i, 40))
for k in sorted(g):
    v = g[k]
    print(f"    @58={k:>3} (/16={k//16})  n={len(v):<4} "
          f"@40 均值={st.mean(v):6.1f} 中位={int(st.median(v)):>3} 范围 {min(v)}..{max(v)}")

print("\n  @58 分组下的 @43 统计:")
g43 = {}
for i in range(N):
    g43.setdefault(f(b1, i, 58), []).append(f(b1, i, 43))
for k in sorted(g43):
    v = g43[k]
    print(f"    @58={k:>3}  n={len(v):<4} @43 均值={st.mean(v):5.1f} 范围 {min(v)}..{max(v)}")
