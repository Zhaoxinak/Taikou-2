#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, struct
from collections import Counter
GAME="F:/Games/Taikou2"
def load(fn):
    b=open(os.path.join(GAME,fn),'rb').read()
    assert b[:16]==b"TAIKOU2_SCENARIO"
    body=b[16:16+833*49]
    return [body[i*49:i*49+49] for i in range(833)]

r1=load("SNDATA1.TR2")
N=len(r1)

def hexrec(rec):
    return " ".join(f"{rec[i]:02x}" for i in range(49))

print("=== 多记录完整十六进制 (S1) ===")
for idx in (0,1,2,3,4,5,10,50,100,500,832):
    rec=r1[idx]
    print(f"\n-- record {idx} --")
    print("  ", hexrec(rec))

# 区域特征
print("\n=== 各字节偏移特征 (S1, 833 记录) ===")
print(f"{'off':>3} {'uniq':>5} {'min':>4} {'max':>4} {'bool?':>6} {'zero%':>6}  top4")
for o in range(49):
    col=[r1[i][o] for i in range(N)]
    uniq=len(set(col))
    mn=min(col); mx=max(col)
    only01 = (set(col)<=set([0,1]))
    zero=sum(1 for v in col if v==0)/N
    c=Counter(col)
    top=",".join(f"{v:02x}:{n}" for v,n in c.most_common(4))
    print(f"{o:>3} {uniq:>5} {mn:>4} {mx:>4} {str(only01):>6} {zero*100:>5.1f}%  {top}")

# 头部 4 字节是否唯一 (ID vs 校验)
hdr=[bytes(r1[i][:4]) for i in range(N)]
print(f"\n=== 头部4字节 ===")
print(f"唯一头部值数: {len(set(hdr))} / {N}")
hc=Counter(hdr)
print("最常见头部:", ", ".join(f"{k.hex()}:{v}" for k,v in hc.most_common(5)))

# 标志区 bytes 4-27 的模式
print(f"\n=== 标志区 bytes 4-27 (24字节) 分析 ===")
# 是否所有记录该区都是 01/00?
flagmask_ok=sum(1 for i in range(N) if all(r1[i][o] in (0,1) for o in range(4,28)))
print(f"全部24标志字节均为 0/1 的记录数: {flagmask_ok}/{N}")
# 计算每条记录 flag 数
for idx in (0,1,2,3,4):
    rec=r1[idx]
    flags=[rec[o] for o in range(4,28)]
    n1=sum(flags)
    print(f"  record {idx}: 24flags 中 1 的个数={n1}, 模式={''.join(str(f) for f in flags)}")
