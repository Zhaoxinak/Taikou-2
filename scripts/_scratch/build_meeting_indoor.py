"""
会议/宴席室内背景烘焙（Godot 端用做纹理）。
对应原版 #11：木地板 + 障子屏风 + 榻榻米。
"""
import os
from PIL import Image, ImageDraw

W, H = 1024, 640
ASSET_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
OUT = os.path.normpath(os.path.join(ASSET_DIR, "meeting_indoor.png"))

COL_WOOD = (90, 55, 30)
COL_WOOD_LT = (130, 85, 50)
COL_WOOD_DK = (60, 35, 18)
COL_WOOD_WALL = (75, 50, 30)
COL_SHOJI_PAPER = (240, 230, 200)
COL_SHOJI_GRID = (140, 100, 60)
COL_TATAMI = (90, 130, 80)
COL_TATAMI_DK = (70, 105, 60)
COL_TATAMI_EDGE = (50, 80, 45)


def draw_indoor():
    img = Image.new("RGB", (W, H), COL_WOOD_WALL)
    d = ImageDraw.Draw(img)

    # ——上半：木墙 + 障子屏风（右侧大块）
    wall_top = 0
    d.rectangle([(0, wall_top), (W, 220)], fill=COL_WOOD_WALL)
    # 墙横纹
    for y in range(wall_top, 220, 16):
        d.line([(0, y), (W, y)], fill=(60, 40, 22), width=1)

    # 障子屏风（右侧 3×3 拉门）
    sx, sy, sw, sh = 600, 8, 410, 200
    d.rectangle([(sx, sy), (sx + sw, sy + sh)], fill=COL_SHOJI_PAPER)
    # 横向木格
    n_rows = 3
    n_cols = 4
    cell_w = sw / n_cols
    cell_h = sh / n_rows
    for i in range(1, n_cols):
        x = sx + i * cell_w
        d.line([(x, sy), (x, sy + sh)], fill=COL_SHOJI_GRID, width=2)
    for i in range(1, n_rows):
        y = sy + i * cell_h
        d.line([(sx, y), (sx + sw, y)], fill=COL_SHOJI_GRID, width=2)
    # 障子外框
    d.rectangle([(sx - 1, sy - 1), (sx + sw + 1, sy + sh + 1)], outline=COL_SHOJI_GRID, width=3)
    # 障子下方小窗（带格）
    win_y0 = sy + sh
    win_h = 80
    d.rectangle([(sx, win_y0), (sx + sw, win_y0 + win_h)], fill=(50, 32, 20))
    d.rectangle([(sx, win_y0), (sx + sw, win_y0 + win_h)], outline=COL_SHOJI_GRID, width=2)
    # 小窗内
    d.rectangle([(sx + 10, win_y0 + 8), (sx + sw - 10, win_y0 + win_h - 8)], fill=(40, 25, 15))

    # ——下半：木地板
    floor_y0 = 220
    d.rectangle([(0, floor_y0), (W, H)], fill=COL_WOOD)
    for y in range(floor_y0, H, 6):
        d.line([(0, y), (W, y)], fill=COL_WOOD_LT, width=1)
    for x in range(0, W, 56):
        d.line([(x, floor_y0), (x, H)], fill=COL_WOOD_DK, width=1)

    # 榻榻米（中央偏上，绿色）
    tx, ty, tw, th = 380, 280, 280, 90
    d.rectangle([(tx, ty), (tx + tw, ty + th)], fill=COL_TATAMI)
    d.rectangle([(tx, ty), (tx + tw, ty + th)], outline=COL_TATAMI_EDGE, width=3)
    cells = 4
    for i in range(1, cells):
        d.line(
            [(tx + i * (tw / cells), ty), (tx + i * (tw / cells), ty + th)],
            fill=COL_TATAMI_EDGE, width=1,
        )
    # 榻榻米上下边框（暗金滚边）
    d.rectangle([(tx - 6, ty - 6), (tx + tw + 6, ty + th + 6)], outline=COL_TATAMI_DK, width=2)
    # 主君席稍高台阶
    d.rectangle([(tx - 20, ty - 12), (tx + tw + 20, ty + 2)], fill=(50, 32, 18))
    d.rectangle([(tx - 20, ty - 12), (tx + tw + 20, ty + 2)], outline=(35, 22, 12), width=1)

    return img


def main():
    img = draw_indoor()
    img.save(OUT, "PNG", optimize=True)
    print(f"OK: {OUT}  ({os.path.getsize(OUT)} bytes)")


if __name__ == "__main__":
    main()
