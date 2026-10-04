# -*- coding: utf-8 -*-
"""a_text2.py — 找文字行块 + 每块的 x 范围
用法: python a_text2.py <png> y0 y1 x0 x1 [thr]
"""
import sys
from PIL import Image
import numpy as np

p, y0, y1, x0, x1 = sys.argv[1], *[int(v) for v in sys.argv[2:6]]
thr = int(sys.argv[6]) if len(sys.argv) > 6 else 4
im = Image.open(p).convert('RGB')
a = np.asarray(im).astype(np.int16)
# 只取偶数行(2x 上采样, 奇偶相同)
a = a[::2, ::2]
r = a[:, :, 0]; g = a[:, :, 1]; b = a[:, :, 2]
dark = (r < 110) & (g < 110) & (b < 120)
Y0, Y1, X0, X1 = y0 // 2, y1 // 2, x0 // 2, x1 // 2
sub = dark[Y0:Y1, X0:X1]
rows = sub.sum(axis=1)
bands = []
i = 0
while i < len(rows):
    if rows[i] >= thr:
        j = i
        while j < len(rows) and rows[j] >= thr:
            j += 1
        bands.append((i, j - 1))
        i = j
    else:
        i += 1
print('>>> 文字行块 (逻辑 y):')
for (i, j) in bands:
    seg = sub[i:j + 1]
    cols = seg.sum(axis=0)
    xs = [k for k, v in enumerate(cols) if v > 0]
    if not xs:
        continue
    print('  y %4d..%-4d (thick %2d)  x %4d..%-4d  dark=%d' %
          (Y0 + i, Y0 + j, j - i + 1, X0 + xs[0], X0 + xs[-1], int(seg.sum())))
