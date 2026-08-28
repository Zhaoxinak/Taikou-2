"""
世界地图预览生成（#4 原版参照，俯视战略地图）
- 浅蓝顶菜单条 + 深灰底命令条
- 绿陆地 / 深蓝海（日本列岛轮廓 = 程序化 4 大岛多边形，套在 48x37 网格）
- 92 城标记：按势力着色（玩家=金/势力A=红/势力B=蓝/势力C=绿/其余=青灰）
- 选中城：白环 + 金色名字标签
- 左上侧边状态面板：日期 / 玩家 / 金钱 / 体力
- 右侧小信息窗：选中城名 + 说明
"""
import os, json
from PIL import Image, ImageDraw, ImageFont

GRID_W, GRID_H = 48, 37
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "assets"))
OUT = os.path.join(ASSET_DIR, "worldmap_preview.png")

# 画布尺寸（贴合原版 642x447 观感，用 640x400 引擎基准）
W, H = 640, 400
TOP_BAR = 18          # 顶部菜单条高
STATUS_H = 30         # 顶部状态条高
BOTTOM_BAR = 30       # 底部命令条高
MAP_X0, MAP_Y0 = 0, TOP_BAR + STATUS_H
MAP_W, MAP_H = W, H - MAP_Y0 - BOTTOM_BAR

# 配色
COL_TOPBAR = (204, 223, 226)
COL_BOTTOM = (54, 57, 56)
COL_STATUS = (20, 30, 60)
COL_SEA = (14, 30, 70)
COL_SEA_DK = (10, 22, 55)
COL_LAND = (86, 120, 64)
COL_LAND_DK = (64, 96, 48)
COL_LAND_LT = (110, 145, 82)
COL_GOLD = (220, 190, 90)
COL_WHITE = (240, 240, 240)
COL_TEXT = (235, 230, 210)

# 势力配色（按 enemy 字段 / id 哈希）
CLAN_COLORS = {
    "nobunaga": (200, 50, 50),     # 织田=红
    "asai": (60, 90, 170),         # 浅井=蓝
    "saito": (70, 140, 80),        # 斋藤=绿
}
PALETTE = [(180, 80, 60), (70, 110, 160), (90, 150, 90),
           (170, 150, 70), (120, 90, 150), (60, 140, 150),
           (160, 110, 70), (110, 120, 130)]


def load_towns():
    with open(os.path.join(SCRIPT_DIR, "towns.json"), encoding="utf-8") as f:
        d = json.load(f)
    return d["towns"]


def load_font(size, bold=False):
    for c in ["C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/msgothic.ttc",
              "C:/Windows/Fonts/msgothic.ttf",
              "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


def japan_land_mask():
    """程序化日本列岛陆地掩码（48x37 网格）。
    方法：以 92 城坐标点云为种子，做受控膨胀（距离场），
    保证每座城都在陆地上，海路（岛屿间距大处）自然留白。
    返回 set of (x,y) 陆地格。"""
    towns = load_towns()
    seeds = [(int(t["map_x"]), int(t["map_y"])) for t in towns
             if isinstance(t.get("map_x"), int)]
    R = 2.0        # 单城膨胀半径
    BRIDGE = 3.6   # 桥接阈值：同岛相邻城(距<=BRIDGE)才连，远的海峡保留
    dist = [[9999] * GRID_W for _ in range(GRID_H)]
    bridge = [[False] * GRID_W for _ in range(GRID_H)]
    for y in range(GRID_H):
        for x in range(GRID_W):
            best = 9999.0
            for (sx, sy) in seeds:
                dd = ((x - sx) ** 2 + (y - sy) ** 2) ** 0.5
                if dd < best:
                    best = dd
            dist[y][x] = best
            # 该格是否紧邻某城（用于桥接判定）
            for (sx, sy) in seeds:
                if ((x - sx) ** 2 + (y - sy) ** 2) ** 0.5 <= BRIDGE:
                    bridge[y][x] = True
                    break
    land = set()
    for y in range(GRID_H):
        for x in range(GRID_W):
            if dist[y][x] <= R:
                land.add((x, y))
    # 桥接：两城之间、距各自城都 <= BRIDGE 的格（即两城间距 <= 2*BRIDGE）才填，
    # 这样仅连接近邻城，远的海峡（如濑户内海）留白
    for y in range(GRID_H):
        for x in range(GRID_W):
            if (x, y) in land:
                continue
            if not bridge[y][x]:
                continue
            # 检查是否有另一座城，使本格处于两城桥接带
            for (sx, sy) in seeds:
                d1 = ((x - sx) ** 2 + (y - sy) ** 2) ** 0.5
                if d1 > BRIDGE:
                    continue
                for (sx2, sy2) in seeds:
                    if (sx2, sy2) == (sx, sy):
                        continue
                    d2 = ((x - sx2) ** 2 + (y - sy2) ** 2) ** 0.5
                    if d2 <= BRIDGE:
                        land.add((x, y))
                        break
                else:
                    continue
                break
    return land


def main():
    towns = load_towns()
    land = japan_land_mask()

    # 检查城堡是否落在陆地，统计
    off = [t["name"] for t in towns
           if (int(t["map_x"]), int(t["map_y"])) not in land]
    print(f"[land] land cells={len(land)}, castles off-land={len(off)}")
    if off:
        print("  off-land sample:", off[:6])

    img = Image.new("RGB", (W, H), COL_SEA)
    d = ImageDraw.Draw(img)

    # ---- 海背景 + 浪点 ----
    d.rectangle([(0, MAP_Y0), (W, MAP_Y0 + MAP_H)], fill=COL_SEA)
    for y in range(MAP_Y0, MAP_Y0 + MAP_H, 6):
        for x in range(0, W, 7):
            if ((x + y) // 7) % 3 == 0:
                d.point((x + (y // 6) % 2 * 3, y), fill=COL_SEA_DK)

    # ---- 陆地 ----
    sx = MAP_W / GRID_W
    sy = MAP_H / GRID_H
    for (gx, gy) in land:
        x0 = MAP_X0 + gx * sx
        y0 = MAP_Y0 + gy * sy
        d.rectangle([(x0, y0), (x0 + sx + 1, y0 + sy + 1)], fill=COL_LAND)
    # 陆地高光（内部）
    for (gx, gy) in land:
        if (gx + 1, gy) in land and (gx, gy + 1) in land and \
           (gx - 1, gy) in land and (gx, gy - 1) in land:
            x0 = MAP_X0 + gx * sx
            y0 = MAP_Y0 + gy * sy
            d.rectangle([(x0 + sx * 0.25, y0 + sy * 0.25),
                         (x0 + sx * 0.75, y0 + sy * 0.75)], fill=COL_LAND_LT)

    # ---- 城堡标记 ----
    selected = towns[0]  # 默认选中第一城（演示）
    for t in towns:
        gx, gy = int(t["map_x"]), int(t["map_y"])
        cx = MAP_X0 + (gx + 0.5) * sx
        cy = MAP_Y0 + (gy + 0.5) * sy
        enemy = t.get("enemy", "")
        if enemy in CLAN_COLORS:
            col = CLAN_COLORS[enemy]
        else:
            col = PALETTE[t["id"] % len(PALETTE)]
        r = 3
        d.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=col,
                  outline=(20, 20, 20), width=1)
        if t is selected:
            d.ellipse([(cx - r - 2, cy - r - 2), (cx + r + 2, cy + r + 2)],
                      outline=COL_WHITE, width=2)
            # 名字标签
            f = load_font(11, True)
            name = t["name"]
            tw = d.textlength(name, font=f)
            d.rectangle([(cx - tw / 2 - 3, cy - r - 16),
                         (cx + tw / 2 + 3, cy - r - 4)], fill=(0, 0, 0))
            d.text((cx - tw / 2, cy - r - 15), name, font=f, fill=COL_GOLD)

    # ---- 顶部菜单条 ----
    d.rectangle([(0, 0), (W, TOP_BAR)], fill=COL_TOPBAR)
    f = load_font(12, True)
    d.text((8, 3), "太閤立志傳 II", font=f, fill=(20, 20, 20))
    d.text((W - 150, 3), "終了(X)  版本情報(V)", font=load_font(11),
           fill=(20, 20, 20))

    # ---- 顶部状态条 ----
    d.rectangle([(0, TOP_BAR), (W, TOP_BAR + STATUS_H)], fill=COL_STATUS)
    fst = load_font(12)
    d.text((10, TOP_BAR + 7), "1560年 5月21日", font=fst, fill=COL_GOLD)
    d.text((180, TOP_BAR + 7), "羽柴秀吉", font=fst, fill=COL_TEXT)
    d.text((320, TOP_BAR + 7), "金 1200貫", font=fst, fill=COL_TEXT)
    d.text((470, TOP_BAR + 7), "體力 80/100", font=fst, fill=COL_TEXT)
    d.line([(0, TOP_BAR + STATUS_H), (W, TOP_BAR + STATUS_H)],
           fill=(120, 130, 150), width=1)

    # ---- 右侧小信息窗（选中城）----
    info_w, info_h = 180, 70
    ix, iy = W - info_w - 8, MAP_Y0 + 8
    d.rectangle([(ix, iy), (ix + info_w, iy + info_h)], fill=(10, 18, 40))
    d.rectangle([(ix, iy), (ix + info_w, iy + info_h)],
                outline=COL_GOLD, width=1)
    d.text((ix + 8, iy + 8), selected["name"], font=load_font(13, True),
           fill=COL_GOLD)
    # 简单说明（取 desc 前段）
    desc = selected.get("desc", "")
    d.text((ix + 8, iy + 30), desc[:18], font=load_font(10), fill=COL_TEXT)

    # ---- 底部命令条 ----
    d.rectangle([(0, H - BOTTOM_BAR), (W, H)], fill=COL_BOTTOM)
    cmds = ["行軍", "外交", "仕官", "情報", "機能"]
    cw = 100
    for i, c in enumerate(cmds):
        bx = 20 + i * cw
        d.rectangle([(bx, H - BOTTOM_BAR + 5), (bx + cw - 10, H - 5)],
                    outline=(150, 150, 150), width=1)
        d.text((bx + 12, H - BOTTOM_BAR + 9), c, font=load_font(12),
               fill=COL_TEXT)

    img.save(OUT, "PNG", optimize=True)
    print(f"OK: {OUT} ({os.path.getsize(OUT)} bytes)")

    # ---- 另存底图（仅海+陆地，无城标/无UI），供 Godot 端 TextureRect 加载 ----
    base = Image.new("RGB", (W, H), (0, 0, 0))
    bd = ImageDraw.Draw(base)
    bd.rectangle([(0, MAP_Y0), (W, MAP_Y0 + MAP_H)], fill=COL_SEA)
    for y in range(MAP_Y0, MAP_Y0 + MAP_H, 6):
        for x in range(0, W, 7):
            if ((x + y) // 7) % 3 == 0:
                bd.point((x + (y // 6) % 2 * 3, y), fill=COL_SEA_DK)
    for (gx, gy) in land:
        x0 = MAP_X0 + gx * sx
        y0 = MAP_Y0 + gy * sy
        bd.rectangle([(x0, y0), (x0 + sx + 1, y0 + sy + 1)], fill=COL_LAND)
    for (gx, gy) in land:
        if (gx + 1, gy) in land and (gx, gy + 1) in land and \
           (gx - 1, gy) in land and (gx, gy - 1) in land:
            x0 = MAP_X0 + gx * sx
            y0 = MAP_Y0 + gy * sy
            bd.rectangle([(x0 + sx * 0.25, y0 + sy * 0.25),
                          (x0 + sx * 0.75, y0 + sy * 0.75)], fill=COL_LAND_LT)
    base_path = os.path.join(ASSET_DIR, "worldmap_base.png")
    base.save(base_path, "PNG", optimize=True)
    print(f"OK: {base_path} ({os.path.getsize(base_path)} bytes)")


if __name__ == "__main__":
    main()
