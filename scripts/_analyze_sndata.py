#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SNDATA1/2.TR2 字段语义逆向。
策略：
1) 解析 833×49B 记录（跳过 16B 签名）
2) 逐字节比较 S1 vs S2：差异计数高 = 场景可变字段(状态)，低=静态(类型/ID)
3) 每偏移统计 min/max/唯一值数/常见值
4) 打印 record 0/1/2 完整十六进制 + 注释
5) 与 BSDATA(700 武将) 数量对比，推断实体类型
"""
import os, struct

GAME="F:/Games/Taikou2"
def load(fn):
    p=os.path.join(GAME,fn)
    b=open(p,'rb').read()
    assert b[:16]==b"TAIKOU2_SCENARIO", b[:16]
    hdr=b[:16]
    body=b[16:]
    # 尾 23B
    recs=[body[i*49:i*49+49] for i in range(len(body)//49)]
    tail=body[len(recs)*49:]
    return hdr, recs, tail

h1,r1,t1=load("SNDATA1.TR2")
h2,r2,t2=load("SNDATA2.TR2")
print(f"签名: {h1.decode('ascii')}")
print(f"场景1 记录数: {len(r1)}  场景2 记录数: {len(r2)}")
print(f"尾: S1={t1.hex()}  S2={t2.hex()}")
assert len(r1)==len(r2)==833

N=len(r1)
# 逐字节差异分析
print("\n=== 逐字节 S1 vs S2 差异 + 值分布 (offset: diff% / uniq / min-max / 常见值) ===")
print(f"{'off':>3} {'diff':>5} {'uniq':>5} {'min':>4} {'max':>4}  top-values")
diffcount=[0]*49
uniqvals=[set() for _ in range(49)]
mins=[255]*49; maxs=[0]*49
for i in range(N):
    for o in range(49):
        a=r1[i][o]; b=r2[i][o]
        if a!=b: diffcount[o]+=1
        uniqvals[o].add(a)
        mins[o]=min(mins[o],a); maxs[o]=max(maxs[o],a)
for o in range(49):
    # 统计 S1 中该偏移的最常见值
    from collections import Counter
    c=Counter(r1[i][o] for i in range(N))
    top=",".join(f"{v:02x}:{n}" for v,n in c.most_common(4))
    d=diffcount[o]
    bar="#"*(d//20)
    print(f"{o:>3} {d:>5} {len(uniqvals[o]):>5} {mins[o]:>4} {maxs[o]:>4}  {top}  {bar}")

# 把记录按"是否全 0/全同"分组观察
print("\n=== record 0,1,2 完整十六进制 (S1) ===")
for idx in (0,1,2,100,500,832):
    rec=r1[idx]
    hexs=" ".join(f"{rec[i]:02x}" for i in range(49))
    # 尝试按 16-bit 大端解读部分字段
    print(f"\n-- record {idx} (S1) --")
    print(f"  hex: {hexs}")
    # 展示可能的 uint16 字段候选
    u16=[struct.unpack(">H",rec[i*2:i*2+2])[0] for i in range(0,24,2)]
    print(f"  u16@0,2,4..: {u16}")
    u8pairs=[(rec[i],rec[i+1]) for i in range(0,49,2)]
