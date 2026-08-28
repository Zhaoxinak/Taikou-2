#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, struct
from collections import Counter
GAME="F:/Games/Taikou2"
def load(fn):
    b=open(os.path.join(GAME,fn),'rb').read()
    assert b[:16]==b"TAIKOU2_SCENARIO"
    return [b[16+i*49:16+i*49+49] for i in range(len(b[16:])//49)]
r1=load("SNDATA1.TR2"); r2=load("SNDATA2.TR2")
N=len(r1)

def u16(rec,o): 
    return struct.unpack("<H", rec[o:o+2])[0] if o+2<=len(rec) else None
def u8(rec,o): return rec[o]

# 关键偏移（来自反汇编字段解析函数）
# 0x10(word, 8个子系统的主字段), 0x14(word), 0x18(word), 0xa(u8), 0xb(u8), 0xc(u8), 0xd(u8), 0x3c/0x3d/0x3e(u8)
print(f"N={N}")
for label,off,kind in [("off0x10 u16",0x10,'u16'),("off0x14 u16",0x14,'u16'),
                        ("off0x18 u16",0x18,'u16'),("off0x0c u8",0xc,'u8'),
                        ("off0x0d u8",0xd,'u8'),("off0x0a u8",0xa,'u8'),
                        ("off0x0b u8",0xb,'u8'),("off0x3c u8",0x3c,'u8'),
                        ("off0x3d u8",0x3d,'u8'),("off0x3e u8",0x3e,'u8'),
                        ("off0x00 u16",0,'u16'),("off0x04 u16",4,'u16')]:
    vals1=[ (u16(r1[i],off) if kind=='u16' else u8(r1[i],off)) for i in range(N)]
    vals2=[ (u16(r2[i],off) if kind=='u16' else u8(r2[i],off)) for i in range(N)]
    c1=Counter(vals1)
    rng=(min(vals1),max(vals1))
    # 看是否像 ID (值密集在 0..N 附近)
    lt_833=sum(1 for v in vals1 if v<N)
    print(f"\n{label}: range={rng} 唯一值={len(c1)}  <N比例={lt_833/N:.2f}")
    print(f"   S1 top: {c1.most_common(8)}")
    # 与 S2 同偏移差异率
    diff=sum(1 for i in range(N) if vals1[i]!=vals2[i])/N
    print(f"   S1 vs S2 差异率={diff:.2f}")

# 测试假设: record[0x10] 是否 = 武将索引 (0..699)？
# 若 700 个真实记录 + 133 其他，应看到大量 0..699 值
print("\n=== 假设检验: off0x10(u16) 是否武将索引? ===")
v10=[u16(r1[i],0x10) for i in range(N)]
in_range=sum(1 for v in v10 if 0<=v<700)
print(f"off0x10 in [0,700): {in_range}/{N}")
in_range2=sum(1 for v in v10 if 0<=v<833)
print(f"off0x10 in [0,833): {in_range2}/{N}")
print(f"off0x10 histogram of //100: {Counter(v//100 for v in v10)}")
