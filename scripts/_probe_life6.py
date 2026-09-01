# -*- coding: utf-8 -*-
"""决定性检验: @40&31 / @43 / @58 是否为生年的函数。"""
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

from collections import Counter, defaultdict

B1 = _ROOT + '/Taikou2 Original/BSDATA1.TR2'
b1 = open(B1, "rb").read()
REC, N = 59, 700
birth = [1490 + (b1[REC * i + 39] & 0x7F) for i in range(N)]


def F(i, off):
    return b1[REC * i + off]


print("=" * 80)
print("A. 每个生年 -> @40&31 取值集合 (若唯一则该字段是生年的函数)")
print("=" * 80)
m = defaultdict(set)
for i in range(N):
    m[birth[i]].add(F(i, 40) & 31)
multi = {k: v for k, v in m.items() if len(v) > 1}
print(f"  生年取值 {len(m)} 个, 其中 @40&31 不唯一的 {len(multi)} 个")
print(f"  样例(前 12 个生年): " +
      ", ".join(f"{k}->{sorted(m[k])}" for k in sorted(m)[:12]))
# 若近似函数, 看是否 @40&31 == max(0, 生年 - K)
best = None
for K in range(1480, 1600):
    hit = sum(1 for i in range(N) if max(0, birth[i] - K) == (F(i, 40) & 31))
    if best is None or hit > best[1]:
        best = (K, hit)
print(f"  max(0, 生年-K) == @40&31 最佳: K={best[0]} 命中 {best[1]}/700")
best2 = None
for K in range(0, 200):
    hit = sum(1 for i in range(N) if (birth[i] + K) % 32 == (F(i, 40) & 31))
    if best2 is None or hit > best2[1]:
        best2 = (K, hit)
print(f"  (生年+K) mod 32 == @40&31 最佳: K={best2[0]} 命中 {best2[1]}/700")

print("\n" + "=" * 80)
print("B. 生年 -> @43 / @58 是否唯一")
print("=" * 80)
for off, lbl in ((43, "@43"), (58, "@58")):
    mm = defaultdict(set)
    for i in range(N):
        mm[birth[i]].add(F(i, off))
    mu = {k: v for k, v in mm.items() if len(v) > 1}
    print(f"  {lbl}: 生年->{lbl} 不唯一的 {len(mu)}/{len(mm)}  ⇒ "
          f"{'是生年的函数' if not mu else '不是生年的函数'}")

print("\n" + "=" * 80)
print("C. @40>>5 (A) 与 @40&31 (B) 的联合分布")
print("=" * 80)
c = Counter((F(i, 40) >> 5, F(i, 40) & 31) for i in range(N))
print("   A=0..7 行, B 取值数:")
for a in range(8):
    bs = {b for (aa, b) in c if aa == a}
    n = sum(v for (aa, b), v in c.items() if aa == a)
    print(f"    A={a}: n={n:<4} B 取值={sorted(bs)[:16]}{' ...' if len(bs) > 16 else ''}")

print("\n" + "=" * 80)
print("D. @40 全值分布(按 32 分组) —— 看 B 的语义边界")
print("=" * 80)
c40 = Counter(F(i, 40) for i in range(N))
for v in sorted(c40):
    print(f"    @40={v:>3} (= {v>>5}*32 + {v&31:<2})  n={c40[v]}")
