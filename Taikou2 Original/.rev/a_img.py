# -*- coding: utf-8 -*-
"""a_img.py — 在截图里量卡片边框 / 文字行位置
用法: python a_img.py <png> [mode]
"""
import sys
from PIL import Image
import numpy as np

p = sys.argv[1]
im = Image.open(p).convert('RGB')
a = np.asarray(im).astype(np.int16)
H, W, _ = a.shape
print('size', W, H)


def runs(mask, minlen):
    out = []
    i = 0
    n = len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            if j - i >= minlen:
                out.append((i, j - 1, j - i))
            i = j
        else:
            i += 1
    return out


# 卡片的深红内边框: 找一条水平线里"明显偏红偏暗"的列
def reddish(px):
    r, g, b = int(px[0]), int(px[1]), int(px[2])
    return r > 90 and g < 80 and b < 80 and r - g > 40


if len(sys.argv) > 2 and sys.argv[2] == 'scan':
    for y in [int(v) for v in sys.argv[3].split(',')]:
        row = a[y]
        m = np.array([reddish(row[x]) for x in range(W)])
        print('y=%d 红列段:' % y, runs(m, 3)[:24])
    for x in [int(v) for v in sys.argv[4].split(',')] if len(sys.argv) > 4 else []:
        col = a[:, x]
        m = np.array([reddish(col[y]) for y in range(H)])
        print('x=%d 红行段:' % x, runs(m, 3)[:24])
else:
    # 默认: 找卡片边框 —— 逐行统计"红列段"最长的若干行
    solid = np.zeros(H, dtype=int)
    for y in range(H):
        row = a[y]
        m = np.array([reddish(row[x]) for x in range(W)])
        r = runs(m, 40)
        solid[y] = sum(t[2] for t in r)
    top = np.argsort(-solid)[:14]
    print('红长横线最强的行:', sorted((int(v), int(solid[v])) for v in top))
