#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""战斗地图数据逆向：解压 .LZW，比对 HKMAPDAT.LZW vs HJMAPDAT.DAT，分析 HJMAPDAT.DAT 裸结构。"""
import os, struct
sys_path = os.path.join(os.path.dirname(__file__))
import sys; sys.path.insert(0, sys_path)
from real_assets import ls11_decompress

GAME = "F:/Games/Taikou2"

def load_raw(fn):
    return open(os.path.join(GAME, fn), 'rb').read()

def load_lzw(fn):
    raw = open(os.path.join(GAME, fn), 'rb').read()
    try:
        return ls11_decompress(raw)
    except Exception as e:
        return None

files = ["HBMAP.LZW","HKMAP.LZW","HJMAP.LZW","HKMAPDAT.LZW","HKMAPNEW.LZW","HJMAPDAT.DAT","HBOBJ.DAT"]
print("=== 解压/读取各文件 ===")
data = {}
for fn in files:
    if fn.endswith(".LZW"):
        dec = load_lzw(fn)
        if dec is None:
            print(f"  {fn}: LZW解压失败")
            data[fn] = None
        else:
            print(f"  {fn}: 压缩={os.path.getsize(os.path.join(GAME,fn))} 解压={len(dec)}")
            data[fn] = dec
    else:
        d = load_raw(fn)
        print(f"  {fn}: 裸={len(d)}")
        data[fn] = d

# 比对 HKMAPDAT.LZW 解压 vs HJMAPDAT.DAT 裸
hk_lzw = data.get("HKMAPDAT.LZW")
hj_dat = data.get("HJMAPDAT.DAT")
if hk_lzw and hj_dat:
    print(f"\n=== HKMAPDAT.LZW 解压({len(hk_lzw)}) vs HJMAPDAT.DAT 裸({len(hj_dat)}) ===")
    print(f"  长度差: {len(hk_lzw)-len(hj_dat)}")
    # 看 HJMAPDAT.DAT 是否 = HKMAPDAT.LZW 解压的后段（去掉头部）
    # 尝试：HKMAPDAT.LZW 解压去掉前 N 字节 == HJMAPDAT.DAT
    best=None
    for N in range(0, 2048):
        if hk_lzw[N:N+len(hj_dat)] == hj_dat:
            best=N; break
    if best is not None:
        print(f"  HJMAPDAT.DAT == HKMAPDAT.LZW 解压[从偏移 {best} 起]  (头部 {best} 字节为压缩元数据)")
    else:
        # 看末尾是否匹配
        tail = len(hj_dat)
        if hk_lzw[-tail:] == hj_dat:
            print(f"  HJMAPDAT.DAT == HKMAPDAT.LZW 解压尾部（前 {len(hk_lzw)-tail} 字节为额外数据）")
        else:
            # 前缀匹配长度
            m=0
            while m<min(len(hk_lzw),len(hj_dat)) and hk_lzw[m]==hj_dat[m]: m+=1
            print(f"  最长公共前缀: {m} 字节")

# 分析 HJMAPDAT.DAT 裸结构
print(f"\n=== HJMAPDAT.DAT 结构分析 ({len(hj_dat)} B) ===")
hdr = hj_dat[:32]
print(f"  头部32字节 hex: {hdr.hex()}")
print(f"  头部可见 ASCII: {''.join(chr(b) if 32<=b<127 else '.' for b in hdr)}")
# 字节值分布
from collections import Counter
c = Counter(hj_dat)
print(f"  唯一字节值: {len(c)} / 256")
print(f"  top值: {c.most_common(8)}")
# 找可能的维度：枚举 w*h 使 w*h == size 或 size-header
size = len(hj_dat)
print(f"\n  尝试常见瓦片/网格尺寸 (w*h 接近 {size}):")
for w in [64,80,100,128,160,200,230,256,320]:
    if size % w == 0:
        h = size // w
        if h <= 4096:
            print(f"    {w} x {h} = {w*h}  (余 {size - w*h})")
# 也试减去可能头部
print(f"  size-2={-2+size} size-4={-4+size} size-16={-16+size} size-32={-32+size}")
for hdr_sz in [0,2,4,8,16,32]:
    rem = size - hdr_sz
    for w in [64,80,100,128,160,200,256]:
        if rem % w == 0:
            h = rem // w
            if 1 <= h <= 4096:
                print(f"    去头部{hdr_sz}: {w} x {h}, 每格 {rem//(w*h)} B")
                break
