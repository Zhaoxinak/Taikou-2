"""
v9 wallpaper: dense 版（线条更粗更密 + 小卷叶 + 交叉短弧）
目标：让金色尽量多覆盖、深蓝只透细缝
"""
import math
from PIL import Image, ImageDraw

W, H = 640, 400
BG = (8, 32, 74)
LINE_GOLD = (210, 158, 40)
LINE_DARK = (100, 70, 14)
LEAF_GOLD = (235, 180, 55)
LEAF_LITE = (250, 220, 90)
PITH = (255, 240, 145)

img = Image.new('RGB', (W, H), BG)
draw = ImageDraw.Draw(img)

CELL = 56


# 1) 主网格线（粗），画整根水平/竖直线跨满屏
# 横线
for y in range(-CELL, H + CELL, CELL):
    py = y + CELL / 2
    # 整条横线
    draw.line([(0, py), (W, py)], fill=LINE_DARK, width=1)
    # 在每段中点画一条短亮金
    for x in range(-CELL, W, CELL):
        cx = x + CELL / 2
        draw.line([(cx - 12, py), (cx + 12, py)], fill=LINE_GOLD, width=1)

# 竖线
for x in range(-CELL, W + CELL, CELL):
    px = x + CELL / 2
    draw.line([(px, 0), (px, H)], fill=LINE_DARK, width=1)
    for y in range(-CELL, H, CELL):
        cy = y + CELL / 2
        draw.line([(px, cy - 12), (px, cy + 12)], fill=LINE_GOLD, width=1)

# 副对角 (45度短线在每格中心)
for row in range(-CELL, H + CELL, CELL):
    for col in range(-CELL, W + CELL, CELL):
        cx = col + CELL / 2
        cy = row + CELL / 2
        off = CELL / 2 / math.sqrt(2)
        draw.line([(cx - off, cy - off), (cx + off, cy + off)],
                  fill=LINE_GOLD, width=1)
        draw.line([(cx - off, cy + off), (cx + off, cy - off)],
                  fill=LINE_GOLD, width=1)


# 2) 中心 4-瓣小花
def draw_knot(cx, cy):
    for rot in [45, 135, 225, 315]:
        ang = math.radians(rot)
        L = 16
        W_lf = 7
        tx = cx + math.cos(ang) * L
        ty = cy + math.sin(ang) * L
        bx = cx + math.cos(ang) * 4
        by = cy + math.sin(ang) * 4
        perp = ang + math.pi / 2
        along = L * 0.5
        lx = cx + along * math.cos(ang) + W_lf * math.cos(perp)
        ly = cy + along * math.sin(ang) + W_lf * math.sin(perp)
        rx = cx + along * math.cos(ang) - W_lf * math.cos(perp)
        ry = cy + along * math.sin(ang) - W_lf * math.sin(perp)
        draw.polygon([(bx, by), (lx, ly), (tx, ty), (rx, ry)], fill=LEAF_GOLD)
        draw.polygon([(bx, by), (lx, ly), (tx, ty), (rx, ry)], outline=LINE_DARK)
        r = W_lf * 0.5
        draw.ellipse([tx - r, ty - r, tx + r, ty + r], fill=LEAF_LITE)
    r0 = 4
    draw.ellipse([cx - r0, cy - r0, cx + r0, cy + r0], fill=PITH)
    r1 = 2
    draw.ellipse([cx - r1, cy - r1, cx + r1, cy + r1], fill=LEAF_LITE)


for row in range(0, H + CELL, CELL):
    for col in range(0, W + CELL, CELL):
        cx = col + CELL / 2
        cy = row + CELL / 2
        draw_knot(cx, cy)


img.save('assets/menu_wallpaper.png', optimize=True)
print(f'已保存 v9 -> assets/menu_wallpaper.png ({W}x{H})')
