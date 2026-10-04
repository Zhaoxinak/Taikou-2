# -*- coding: utf-8 -*-
"""a_text.py — 在截图里定位深色文字块(用于和逻辑坐标对齐)
用法: python a_text.py <png> y0 y1 x0 x1
"""
import sys
from PIL import Image
import numpy as np

p, y0, y1, x0, x1 = sys.argv[1], *[int(v) for v in sys.argv[2:6]]
im = Image.open(p).convert('RGB')
a = np.asarray(im).astype(np.int16)
r = a[:, :, 0]; g = a[:, :, 1]; b = a[:, :, 2]
dark = (r < 110) & (g < 110) & (b < 120)
sub = dark[y0:y1, x0:x1]
rows = sub.sum(axis=1)
print('行分布 (y, 暗像素数):')
for i, v in enumerate(rows):
    if v > 2:
        print('   %4d %3d' % (y0 + i, v))
