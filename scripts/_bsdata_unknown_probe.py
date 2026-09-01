# -*- coding: utf-8 -*-
"""Exploratory probe: 分析 BSDATA 未定字段的值域分布与关联，为续203 定名提供证据。"""
import os, struct
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
ORIG = os.path.join(ROOT, "Taikou2 Original")
STRIDE = 59; NREC = 700
BS1 = open(os.path.join(ORIG, "BSDATA1.TR2"), "rb").read()
BS2 = open(os.path.join(ORIG, "BSDATA2.TR2"), "rb").read()

def rec(buf, i): return buf[i*STRIDE:(i+1)*STRIDE]
def fld(buf, i, off, sz=1): return int.from_bytes(rec(buf, i)[off:off+sz], "little")
def gbk7(b):
    z = b.split(b"\x00")[0]
    try: return z.decode("gbk")
    except: return None
def name_of(buf, i):
    r = rec(buf, i)
    return (gbk7(r[0:7]) or "?") + (gbk7(r[7:14]) or "?")
def is_ph(buf, i):
    s = gbk7(rec(buf, i)[0:7]); return bool(s) and s.startswith("姓0")
REAL = [i for i in range(NREC) if not is_ph(BS1, i)]

def stats(buf, off, sz=1):
    vals = [fld(buf, i, off, sz) for i in REAL]
    from collections import Counter
    c = Counter(vals)
    return min(vals), max(vals), len(c), c.most_common(8)

print("=== 值分布（BSDATA1, 真实武将 %d 条）===" % len(REAL))
for off, sz, label in [(0x0e,2,"解码器局部A"),(0x12,2,"解码器局部B"),
                       (0x28,1,"->entity+0x1c"),(0x2b,1,"->entity+0x1f"),
                       (0x3a,1,"主角槽/档(高4位)")]:
    lo, hi, ndist, top = stats(BS1, off, sz)
    print("  +0x%02x(%s): min=%d max=%d distinct=%d  top8=%s" % (off, label, lo, hi, ndist, top))

# +0x28 与 age 关联
print("\n=== +0x28 (->entity+0x1c) 细化：倍数/相关 ===")
v28 = [fld(BS1, i, 0x28) for i in REAL]
mult32 = sum(1 for v in v28 if v % 32 == 0)
mult16 = sum(1 for v in v28 if v % 16 == 0)
mult8 = sum(1 for v in v28 if v % 8 == 0)
print("  32倍数: %d / 16倍数: %d / 8倍数: %d (共 %d)" % (mult32, mult16, mult8, len(v28)))
ages = [1560 - (fld(BS1, i, 0x27) + 1490) for i in REAL]
# 年龄 = +0x28 ? 比对
same_as_age = sum(1 for i, a in zip(REAL, ages) if fld(BS1, i, 0x28) == a)
print("  +0x28 == 剧本1年龄(1560-生年) 的条数: %d / %d" % (same_as_age, len(REAL)))
# 生年差
diff = [fld(BS1,i,0x28) - a for i,a in zip(REAL,ages)]
from collections import Counter
print("  +0x28 - age 分布(前10): %s" % Counter(diff).most_common(10))

# +0x2b 关联：与 野心(+0x2f)/忠诚(+0x35)/五维和
print("\n=== +0x2b (->entity+0x1f) 关联 ===")
v2b = [fld(BS1, i, 0x2b) for i in REAL]
amb = [fld(BS1, i, 0x2f) for i in REAL]
five = [sum(fld(BS1,i,0x16+k) for k in range(5)) for i in REAL]
loy = [fld(BS1, i, 0x35) for i in REAL]
def corr(a,b):
    n=len(a); ma=sum(a)/n; mb=sum(b)/n
    cov=sum((x-ma)*(y-mb) for x,y in zip(a,b))
    sa=sum((x-ma)**2 for x in a)**.5; sb=sum((y-mb)**2 for y in b)**.5
    return cov/(sa*sb) if sa*sb else 0
print("  +0x2b vs 野心 r=%.3f / vs 忠诚 r=%.3f / vs 五维和 r=%.3f" % (corr(v2b,amb), corr(v2b,loy), corr(v2b,five)))
print("  +0x2b 值举例(前20): %s" % v2b[:20])

# +0x3a 档 4/5/6 与 五维和/身份 关联
print("\n=== +0x3a>>4 武将档 4/5/6 关联 ===")
tier = {}
for i in REAL:
    k = fld(BS1, i, 0x3a) >> 4
    if k in (4,5,6): tier.setdefault(k, []).append(i)
for k in (4,5,6):
    idxs = tier[k]
    avg5 = sum(sum(fld(BS1,i,0x16+jj) for jj in range(5)) for i in idxs)/len(idxs)
    avgamb = sum(fld(BS1,i,0x2f) for i in idxs)/len(idxs)
    avgloy = sum(fld(BS1,i,0x35) for i in idxs)/len(idxs)
    print("  档%d: n=%d  五维和均值=%.1f  野心均值=%.1f  忠诚均值=%.1f" % (k, len(idxs), avg5, avgamb, avgloy))

# 两剧本一致性：+0x28 / +0x2b / +0x0e / +0x12
print("\n=== 两剧本一致性 ===")
for off, sz in [(0x0e,2),(0x12,2),(0x28,1),(0x2b,1)]:
    same = sum(1 for i in range(NREC) if fld(BS1,i,off,sz)==fld(BS2,i,off,sz))
    print("  +0x%02x: %d/%d 相同" % (off, same, NREC))
