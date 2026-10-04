# -*- coding: utf-8 -*-
"""a_img2.py — 量卡片边框: 纵向/横向长红线的精确位置"""
import sys
from PIL import Image
import numpy as np

p = sys.argv[1]
y0, y1 = (int(v) for v in sys.argv[2].split(','))
im = Image.open(p).convert('RGB')
a = np.asarray(im).astype(np.int16)
H, W, _ = a.shape
r = a[:, :, 0]; g = a[:, :, 1]; b = a[:, :, 2]
red = (r > 90) & (g < 80) & (b < 80) & ((r - g) > 40)
cnt = red[y0:y1].sum(axis=0)
xs = [(int(x), int(cnt[x])) for x in range(W) if cnt[x] > (y1 - y0) * 0.5]
print('竖红列 (y %d..%d):' % (y0, y1), xs)
cnt2 = red[:, :].sum(axis=1)
print('横红行 (全图>600):', [(int(y), int(cnt2[y])) for y in range(H) if cnt2[y] > 600])
