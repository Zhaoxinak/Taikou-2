"""重建原版截图参考网格：动态列数 × 行数，按截图数量自适应。"""
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
from pathlib import Path
import os

orig_dir = Path(_ROOT + '/assets/orig_screens')
out_path = Path(_ROOT + '/assets/orig_grid.png')

# 源: 320×200 缩放
THUMB_W = 280
THUMB_H = 175
COLS = 4           # 4 列更整齐
PAD = 8
LABEL_H = 22
GOLD = (212, 168, 55)
GOLD_DARK = (138, 106, 26)
BG = (10, 14, 28)
WOOD = (58, 36, 16)
TEXT = (240, 232, 208)

# 11 张原版截图标签
labels = [
    "1. 主菜单（深蓝+家纹）",
    "2. 新游戏能力设定",
    "3. 新游戏确认对话框",
    "4. 世界地图（主）",
    "5. 城内面会/修行",
    "6. 城下町（talk/event）",
    "7. 城下町（宴席）",
    "8. 单挑 Battle（4v4 iso）",
    "9. 世界地图（夜）",
    "10. 城下町（主角面板）",
    "11. 会议/宴席（主公议事）",
]

files = sorted([p for p in orig_dir.glob("*_orig.png")],
               key=lambda p: int(p.stem.split("_")[0]))
n = len(files)
if n == 0:
    raise SystemExit("no orig screenshots found")

ROWS = (n + COLS - 1) // COLS

cell_w = THUMB_W + PAD
cell_h = THUMB_H + LABEL_H + PAD
W = COLS * cell_w + PAD
H = ROWS * cell_h + PAD + 32
img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

try:
    font = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 13)
    font_big = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 18)
except Exception:
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msgothic.ttc", 13)
        font_big = ImageFont.truetype("C:/Windows/Fonts/msgothic.ttc", 18)
    except Exception:
        font = ImageFont.load_default()
        font_big = font

d.text((PAD + 4, 6),
       f"原版太閤立志傳 II — 截圖參考（共 {n} 張）",
       fill=GOLD, font=font_big)
d.line([(0, 32), (W, 32)], fill=GOLD_DARK, width=2)

for i in range(n):
    r = i // COLS
    c = i % COLS
    src = files[i]
    src_img = Image.open(src).convert("RGB")
    src_img = src_img.resize((THUMB_W, THUMB_H), Image.NEAREST)
    x = c * cell_w + PAD
    y = r * cell_h + 32 + PAD
    img.paste(src_img, (x, y))
    d.rectangle([(x - 2, y - 2), (x + THUMB_W + 2, y + THUMB_H + 2)], outline=GOLD, width=2)
    d.rectangle([(x - 4, y - 4), (x + THUMB_W + 4, y + THUMB_H + 4)], outline=GOLD_DARK, width=1)
    label_y = y + THUMB_H + 4
    d.rectangle([(x, label_y), (x + THUMB_W, label_y + LABEL_H)], fill=WOOD, outline=GOLD)
    label = labels[i] if i < len(labels) else f"{i+1}."
    d.text((x + 4, label_y + 2), label, fill=TEXT, font=font)

img.save(out_path, optimize=True)
print(f"Grid: {W}x{H}  n={n}  -> {out_path}")
