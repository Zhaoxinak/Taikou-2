#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解压 HKMAPNEW.LZW / HKMAPDAT.DAT，定位 96B 数值记录表（兵种/阵形/计略）。"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
from real_assets import ls11_decompress

GAME = "F:/Games/Taikou2"

def dec(fn):
    raw = open(os.path.join(GAME, fn), 'rb').read()
    if fn.endswith('.LZW') and raw[:4] == b'LS11':
        return ls11_decompress(raw), raw
    return raw, raw

hk_new, hk_new_raw = dec("HKMAPNEW.LZW")
hk_dat_lzw, _      = dec("HKMAPDAT.LZW")
hj_dat             = open(os.path.join(GAME, "HJMAPDAT.DAT"), 'rb').read()

print("=== 解压尺寸 ===")
print("HKMAPNEW.LZW : comp=%d  decomp=%d" % (len(hk_new_raw), len(hk_new)))
print("HKMAPDAT.LZW : decomp=%d" % len(hk_dat_lzw))
print("HJMAPDAT.DAT : raw=%d" % len(hj_dat))

# 头部
for label, d in [("HKMAPNEW", hk_new), ("HJMAPDAT", hj_dat)]:
    print("\n=== %s 头部 32B ===" % label)
    print("  hex:  ", d[:32].hex())
    print("  ascii:", ''.join(chr(b) if 32<=b<127 else '.' for b in d[:32]))

# 96B 记录扫描：在 HKMAPNEW 解压结果里滑窗，找"记录看起来像 stat"的区域
def score_stat_block(buf, off, rec=96, nrec=40):
    """对 [off, off+rec*nrec) 区域评分：返回 (平均每字节小数值比例, 含 u16>255 比例)。"""
    end = off + rec*nrec
    if end > len(buf): nrec = (len(buf)-off)//rec
    if nrec < 5: return (0.0, 0.0)
    small = 0; tot = 0; big = 0
    for r in range(nrec):
        b = buf[off+r*rec:off+r*rec+rec]
        for x in b:
            tot += 1
            if x <= 100: small += 1
        # u16 字段
        for j in range(0, rec-1, 2):
            v = b[j] | (b[j+1]<<8)
            if v > 255: big += 1
    return (small/tot, big/ (tot//2))

print("\n=== HKMAPNEW：扫描 96B 对齐的 stat 区块 ===")
best = []
for off in range(0, max(1, len(hk_new)-96*40), 96):
    s, b = score_stat_block(hk_new, off, 96, 40)
    if s > 0.55:  # 至少 55% 字节是小数值
        best.append((off, s, b))
best.sort(key=lambda x:-x[1])
print("候选区块(top 12, off, small_frac, big_u16_frac):")
for off, s, b in best[:12]:
    print("  0x%05x  small=%.2f  big_u16=%.2f" % (off, s, b))

# 也试 96B 对齐但只看前若干记录
print("\n=== HKMAPNEW：若整体是 96B×N，N=? ===")
N = len(hk_new)//96
print("  len/96 = %d (余 %d)" % (N, len(hk_new)-N*96))
if N > 0:
    print("  前 3 条 96B 记录的 u8 视图:")
    for r in range(3):
        b = hk_new[r*96:r*96+96]
        print("   r%d: %s" % (r, list(b)))
    print("  前 3 条 96B 记录的 u16 视图(前12个):")
    for r in range(3):
        b = hk_new[r*96:r*96+96]
        u = struct.unpack("<48H", b)
        print("   r%d: %s" % (r, list(u[:12])))
