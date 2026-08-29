#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用自相关找 SNDATA 记录尺寸:
  数据区 (跳过 16 字节签名 + 若干头) 内, 若记录尺寸为 R, 则 sd[i] 与 sd[i+R] (同记录内同偏移)
  通常高度相似 (大量默认字段). 对候选 R 计算相关分数, 取峰值.
"""
import sys
sd = open(r"F:/Games/Taikou2/SNDATA1.TR2","rb").read()
# 尝试两个起点: 纯签名后(16) 与 含可能头(24/32)
for start in (16, 24, 32):
    region = sd[start:]
    n = len(region)
    # 仅对"低熵"字节(大量重复值)做相关更稳; 这里直接用原始字节
    best = []
    for S in range(2, 257):
        # 分数 = 相同位置匹配数 / 重叠长度
        match = 0
        L = n - S
        if L <= 0: continue
        step = max(1, L//4000)  # 抽样加速
        cnt = 0
        for i in range(0, L, step):
            if region[i] == region[i+S]:
                match += 1
            cnt += 1
        score = match / cnt
        best.append((score, S))
    best.sort(reverse=True)
    print(f"\n=== start={start} (region {n} bytes) top-12 autocorrelation peaks ===")
    for score, S in best[:12]:
        print(f"  S={S:4d} (0x{S:03x})  score={score:.3f}  -> if N records: {n//S if S else 0}")
print("\nDONE")
