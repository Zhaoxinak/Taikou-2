# -*- coding: utf-8 -*-
"""a_crop.py — 裁剪并放大截图 (NEAREST), 可选画网格
用法: python a_crop.py <png> x0 y0 x1 y1 <scale> <out> [grid]
"""
import sys
from PIL import Image, ImageDraw

p = sys.argv[1]
x0, y0, x1, y1, sc = (int(v) for v in sys.argv[2:7])
out = sys.argv[7]
grid = len(sys.argv) > 8
im = Image.open(p).convert('RGB').crop((x0, y0, x1, y1))
im = im.resize((im.width * sc, im.height * sc), Image.NEAREST)
if grid:
    d = ImageDraw.Draw(im)
    for i in range(0, (x1 - x0) * sc, 10 * sc):
        d.line([(i, 0), (i, im.height)], fill=(255, 0, 255), width=1)
        d.text((i + 2, 2), str(x0 + i // sc), fill=(255, 0, 255))
    for j in range(0, (y1 - y0) * sc, 10 * sc):
        d.line([(0, j), (im.width, j)], fill=(0, 255, 0), width=1)
        d.text((2, j + 2), str(y0 + j // sc), fill=(0, 160, 0))
im.save(out)
print('saved', out, im.size)
