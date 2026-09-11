#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, os, sys
from collections import Counter, defaultdict
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
bs1 = open("Taikou2 Original/BSDATA1.TR2", "rb").read()
bs2 = open("Taikou2 Original/BSDATA2.TR2", "rb").read()
names = json.load(open("scripts/bsdata_names.json", encoding="utf-8"))["BSDATA1"]
REC, N = 59, 700

def fld(b, i, o, n=1):
    return int.from_bytes(b[i * REC + o:i * REC + o + n], "little")

def birth(b, i):
    return (fld(b, i, 0x27) & 0x7F) + 1490

REAL = [i for i, n in enumerate(names) if n and not str(n).startswith("姓")]
print("REAL", len(REAL))

sub = [i for i in REAL if birth(bs1, i) > 1522]
xs = [fld(bs1, i, 0x28) & 0x1F for i in sub]
ys = [birth(bs1, i) for i in sub]
n = len(sub)
mx, my = sum(xs) / n, sum(ys) / n
num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
den = (sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)) ** 0.5
print("sub n", n, "corr lo5 vs birth", num / den)

for y0 in (1540, 1545, 1550, 1555, 1560, 1570):
    eq = sum(1 for i in REAL if (fld(bs1, i, 0x28) & 0x1F) == min(31, max(0, y0 - birth(bs1, i))))
    eq2 = sum(1 for i in REAL if (fld(bs1, i, 0x28) & 0x1F) == min(31, max(0, birth(bs1, i) - y0)))
    print(f"y0={y0} lo5==age {eq}  lo5==birth-y0 {eq2}")

hi = [fld(bs1, i, 0x28) >> 5 for i in REAL]
fsum = [sum(fld(bs1, i, o) for o in range(0x16, 0x1B)) for i in REAL]
rank = [fld(bs1, i, 0x39) & 7 for i in REAL]
arch = [fld(bs1, i, 0x3A) >> 4 for i in REAL]
print("hi3 vs mean五维和:")
by = defaultdict(list)
for h, s in zip(hi, fsum):
    by[h].append(s)
for h in sorted(by):
    print(h, "n", len(by[h]), "mean", round(sum(by[h]) / len(by[h]), 1))

print("hi3 vs arch:")
for h in range(8):
    print(h, dict(Counter(arch[i] for i in range(len(REAL)) if hi[i] == h)))

print("hi3 vs rank:")
for h in range(8):
    print(h, dict(Counter(rank[i] for i in range(len(REAL)) if hi[i] == h)))

print("lo5 when birth<=1522", Counter(fld(bs1, i, 0x28) & 0x1F for i in REAL if birth(bs1, i) <= 1522))
print("sc1/sc2 start probe: mean lo5", sum(fld(bs1, i, 0x28) & 0x1F for i in REAL) / len(REAL),
      sum(fld(bs2, i, 0x28) & 0x1F for i in REAL) / len(REAL))

# For people with lo5!=0, print birth and lo5 relation
print("samples lo5>0:")
for i in REAL:
    lo = fld(bs1, i, 0x28) & 0x1F
    if lo > 0:
        print(i, names[i], "birth", birth(bs1, i), "lo", lo, "birth-lo", birth(bs1, i) - lo,
              "sc2lo", fld(bs2, i, 0x28) & 0x1F)
        if sum(1 for _ in range(1)) and i > 50 and lo > 5:
            pass
# limit
shown = 0
print("--- first 25 nonzero ---")
for i in REAL:
    lo = fld(bs1, i, 0x28) & 0x1F
    if lo == 0:
        continue
    print(i, names[i], "b", birth(bs1, i), "lo", lo, "b-lo", birth(bs1, i) - lo)
    shown += 1
    if shown >= 25:
        break

# Is birth-lo constant?
diffs = Counter(birth(bs1, i) - (fld(bs1, i, 0x28) & 0x1F) for i in REAL if (fld(bs1, i, 0x28) & 0x1F) > 0)
print("birth-lo5 for nonzero:", diffs.most_common(10))
diffs0 = Counter(birth(bs1, i) for i in REAL if (fld(bs1, i, 0x28) & 0x1F) == 0)
print("birth when lo5=0 top", diffs0.most_common(8))
