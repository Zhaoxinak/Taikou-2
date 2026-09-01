"""生成 castle_town_iso.png (1024×640, RGBA) —— 仅 iso 城下町场景，
右侧留透明，供 CastleTown.gd 当 TextureRect 背景使用。

复用预览脚本的 iso 绘制逻辑，但：
- 尺寸 1024×640（Godot 视口）
- 右侧 x>770 区域 alpha=0（让 Godot 面板覆盖）
- 不含任何 UI 文字/面板/图标/日期/顶部条
"""
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>

from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 640
img = Image.new("RGBA", (W, H), (8, 12, 24, 255))
d = ImageDraw.Draw(img)

GOLD_D = (138, 106, 26)
FLOOR = (206, 164, 92)
FLOOR_D = (150, 112, 56)
WALL = (120, 80, 42)
ROOF = (86, 96, 122)


def iso(cx, cy):
    return (OX + (cx - cy) * TW // 2, OY + (cx + cy) * TH // 2)


TW, TH = 44, 22
OX, OY = 250, 80
COLS, ROWS = 14, 11
PANEL_X = 772  # 右侧面板起始 x（此右全透明）


def diamond(x, y, fill, outline, lw=1):
    pts = [(x, y), (x + TW // 2, y + TH // 2), (x, y + TH), (x - TW // 2, y + TH // 2)]
    d.polygon(pts, fill=fill, outline=outline)


def cube(c, r, h, wall_col=WALL, top_col=(224, 188, 120), roof=False, roof_col=ROOF):
    tx, ty = iso(c, r)
    top = [(tx, ty - h), (tx + TW // 2, ty + TH // 2 - h),
           (tx, ty + TH - h), (tx - TW // 2, ty + TH // 2 - h)]
    left = [(tx - TW // 2, ty + TH // 2 - h), (tx, ty + TH - h),
            (tx, ty + TH), (tx - TW // 2, ty + TH // 2)]
    right = [(tx, ty + TH - h), (tx + TW // 2, ty + TH // 2 - h),
             (tx + TW // 2, ty + TH // 2), (tx, ty + TH)]
    d.polygon(left, fill=(int(wall_col[0] * 0.7), int(wall_col[1] * 0.7), int(wall_col[2] * 0.7)))
    d.polygon(right, fill=wall_col)
    d.polygon(top, fill=top_col)
    if roof:
        rh = h + 20
        rtop = [(tx, ty - rh), (tx + TW // 2 + 6, ty + TH // 2 - rh + 10),
                (tx, ty + TH - rh), (tx - TW // 2 - 6, ty + TH // 2 - rh + 10)]
        rleft = [(tx - TW // 2 - 6, ty + TH // 2 - rh + 10), (tx, ty + TH - rh),
                 (tx, ty + TH - h), (tx - TW // 2, ty + TH // 2 - h)]
        rright = [(tx, ty + TH - rh), (tx + TW // 2 + 6, ty + TH // 2 - rh + 10),
                  (tx + TW // 2, ty + TH // 2 - h), (tx, ty + TH - h)]
        d.polygon(rleft, fill=(int(roof_col[0] * 0.7), int(roof_col[1] * 0.7), int(roof_col[2] * 0.7)))
        d.polygon(rright, fill=roof_col)
        d.polygon(rtop, fill=(int(roof_col[0] * 1.15), int(roof_col[1] * 1.15), int(roof_col[2] * 1.15)))


def pine(c, r, scale=1.0):
    tx, ty = iso(c, r)
    h = int(36 * scale)
    w = int(14 * scale)
    for i in range(3):
        yy = ty - i * (h // 3) - (h // 3)
        d.polygon([(tx, yy), (tx - w, yy + h // 3 + 8), (tx + w, yy + h // 3 + 8)],
                  fill=(20 + i * 6, 90 + i * 14, 45 + i * 8))
    d.rectangle([(tx - 3, ty - 3), (tx + 3, ty + 8)], fill=(90, 60, 30))


def npc(c, r, body=(240, 240, 245), hair=(40, 30, 20)):
    tx, ty = iso(c, r)
    d.polygon([(tx - 11, ty + 3), (tx + 11, ty + 3), (tx + 7, ty - 24), (tx - 7, ty - 24)], fill=body)
    d.polygon([(tx - 11, ty + 3), (tx + 11, ty + 3), (tx + 8, ty + 14), (tx - 8, ty + 14)], fill=(40, 60, 110))
    d.ellipse([(tx - 8, ty - 40), (tx + 8, ty - 24)], fill=(235, 200, 170))
    d.pieslice([(tx - 8, ty - 40), (tx + 8, ty - 24)], 180, 360, fill=hair)


# iso 地面（从后往前）
for s in range(0, COLS + ROWS):
    for c in range(COLS):
        r = s_light = s - c
        if r < 0 or r >= ROWS:
            continue
        x, y = iso(c, r)
        if x > PANEL_X:
            continue
        base = FLOOR if ((c + r) % 2 == 0) else FLOOR_D
        diamond(x, y, base, (110, 80, 40))
        d.line([(x - TW // 2 + 3, y + TH // 2), (x, y + TH - 1)], fill=(120, 90, 50), width=1)
        d.line([(x, y + 1), (x + TW // 2 - 3, y + TH // 2)], fill=(120, 90, 50), width=1)

# 建筑
cube(2, 1, 22, roof=True)
cube(10, 2, 18, roof=True, roof_col=(110, 80, 50))
for i in range(4):
    cube(5 + i, 7, 11, wall_col=(150, 110, 60), top_col=(180, 140, 90))
cube(6, 5, 14, wall_col=(220, 220, 225), top_col=(235, 235, 240))
cube(3, 8, 24, wall_col=(90, 120, 160), top_col=(70, 100, 150))
pine(11, 7, 1.0)
pine(1, 9, 0.8)
pine(12, 9, 0.9)
npc(6, 9)
npc(9, 8, body=(230, 225, 210), hair=(30, 25, 15))

# 右侧透明
for y in range(H):
    for x in range(PANEL_X, W):
        img.putpixel((x, y), (0, 0, 0, 0))

img.save(_ROOT + '/assets/castle_town_iso.png')
print("castle_town_iso.png ->", W, "x", H)
