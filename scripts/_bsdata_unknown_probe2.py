# -*- coding: utf-8 -*-
"""续203 补充探针：未定字节的关联分析与解码器溯源。"""
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

import os, struct
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
ORIG = os.path.join(ROOT, "Taikou2 Original")
STRIDE = 59; NREC = 700
BS1 = open(os.path.join(ORIG, "BSDATA1.TR2"), "rb").read()
def rec(buf, i): return buf[i*STRIDE:(i+1)*STRIDE]
def fld(buf, i, off, sz=1): return int.from_bytes(rec(buf, i)[off:off+sz], "little")
def gbk7(b):
    z = b.split(b"\x00")[0]
    try: return z.decode("gbk")
    except: return None
def name_of(buf, i):
    r = rec(buf, i); return (gbk7(r[0:7]) or "?") + (gbk7(r[7:14]) or "?")
def is_ph(buf, i):
    s = gbk7(rec(buf, i)[0:7]); return bool(s) and s.startswith("姓0")
REAL = [i for i in range(NREC) if not is_ph(BS1, i)]
def corr(a,b):
    n=len(a); ma=sum(a)/n; mb=sum(b)/n
    cov=sum((x-ma)*(y-mb) for x,y in zip(a,b))
    sa=sum((x-ma)**2 for x in a)**.5; sb=sum((y-mb)**2 for y in b)**.5
    return cov/(sa*sb) if sa*sb else 0

# 关注字段：+0x28(e+0x1c) +0x29(e+0x1d) +0x2a(e+0x1e) +0x2b(e+0x1f) +0x2c(e+0x20)
FIELDS = {0x28:"e+0x1c",0x29:"e+0x1d",0x2a:"e+0x1e",0x2b:"e+0x1f",0x2c:"e+0x20"}
five = [sum(fld(BS1,i,0x16+k) for k in range(5)) for i in REAL]
loy  = [fld(BS1,i,0x35) for i in REAL]
amb  = [fld(BS1,i,0x2f) for i in REAL]
merit= [fld(BS1,i,0x32,2) for i in REAL]
rank = [fld(BS1,i,0x39)&7 for i in REAL]
print("字段        值域           与五维和r  与忠诚r  与野心r  与功勲r  与職位r")
for off,lab in FIELDS.items():
    v = [fld(BS1,i,off) for i in REAL]
    lo,hi=min(v),max(v)
    print("  +0x%02x(%s) %3d..%3d  r=%.2f  %.2f  %.2f  %.2f  %.2f" % (
        off, lab, lo, hi, corr(v,five), corr(v,loy), corr(v,amb), corr(v,merit), corr(v,rank)))

# +0x28 倍数细分
v28=[fld(BS1,i,0x28) for i in REAL]
from collections import Counter
c=Counter(v28)
print("\n+0x28 值分布(全):", sorted(c.items()))
print("  +0x28 是否 = 0x20*i (i=1..7):", set(v28) <= set(32*k for k in range(0,8)))

# +0x2b 细分布
v2b=[fld(BS1,i,0x2b) for i in REAL]
print("\n+0x2b 值分布(全):", sorted(Counter(v2b).items())[:20])

# +0x29 / +0x2a / +0x2c 分布
for off in (0x29,0x2a,0x2c):
    v=[fld(BS1,i,off) for i in REAL]
    print("+0x%02x 分布(前12): %s" % (off, Counter(v).most_common(12)))

# 解码器：哪些函数读 entity+0x1c/+0x1f？用 EXE 扫 +0x1c 位移出现在 push/add 基址 0x519868 附近?
IMG = open(os.path.join(HERE,_ROOT + '/scripts/_unpacked_mem.bin'),"rb").read()
BASE=0x400000
# 找 entity stride 乘式 + 位移；粗略统计 entity+0x1c 在代码段出现的位置（位移字节 0x1c）
# x86 位移 0x1c 常写作 6b 或 7c（ModRM disp8）。我们不精确解析，改为统计 MOV 类。
# 改为：找 cast-attr getter 0x49af00 的调用方，确认 +0x12..0x15 来源（已定）。
for fn,o in [(0x49AF00,0),(0x49AF50,1),(0x49AFA0,2)]:
    cnt=0
    for k in range(len(IMG)-5):
        if IMG[k]==0xE8:
            rel=struct.unpack_from("<i",IMG,k+1)[0]
            if BASE+k+5+rel==fn: cnt+=1
    print("getter 0x%X 调用点: %d" % (fn,cnt))
