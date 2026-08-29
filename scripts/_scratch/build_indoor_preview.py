"""城内设施室内画面预览渲染（还原原版 #5/#6/#7）。
平视房间：浅蓝顶菜单条 + 木墙/蓝暖帘 + 木棕或绿榻榻米地面
+ 家具(按设施变) + 玩家与 NPC 立绘 + 底部对话框。
输出 assets/indoor_preview.png（默认 teahouse 绿，最特别）与 indoor_preview_dojo.png。
"""
from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 640
TOPBAR_H = 30
FLOOR_Y = 360          # 墙/地分界
DLG_H = 132            # 底部对话框高度
GOLD = (212, 168, 55)
GOLD_DK = (138, 106, 26)
WOOD = (92, 56, 26)
WOOD_HI = (140, 92, 44)
WOOD_DK = (58, 34, 14)
BLUE = (64, 160, 176)        # 蓝暖帘/障子
BLUE_DK = (36, 104, 120)
TATAMI = (150, 176, 120)     # 榻榻米绿
TATAMI_DK = (120, 148, 92)
PAPER = (222, 214, 188)      # 纸障子
DARK = (16, 12, 22)
TEXT = (240, 232, 208)


def font(sz, bold=False):
    for p in ["C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/msgothic.ttc",
              "C:/Windows/Fonts/msyh.ttf"]:
        try:
            return ImageFont.truetype(p, sz)
        except Exception:
            continue
    return ImageFont.load_default()


def draw_char(d, cx, foot_y, scale, robe, skin=(232, 200, 170), hair=(30, 24, 20), band=GOLD):
    """平视立绘占位：头+发髻+和服身。cx=中心, foot_y=脚底 y, scale=像素倍率。"""
    s = scale
    # 身（和服梯形）
    bw = 26 * s
    bh = 92 * s
    top = foot_y - bh
    d.polygon([(cx - bw // 2, foot_y), (cx + bw // 2, foot_y),
               (cx + int(bw * 0.62), top), (cx - int(bw * 0.62), top)], fill=robe)
    # 衣襟
    d.polygon([(cx, top + 6 * s), (cx + 7 * s, top + 30 * s), (cx, foot_y - 8 * s)],
              fill=(max(0, robe[0] - 40), max(0, robe[1] - 40), max(0, robe[2] - 30)))
    # 腰带
    d.rectangle([cx - bw // 2, foot_y - 40 * s, cx + bw // 2, foot_y - 30 * s], fill=band)
    # 头
    hr = 13 * s
    hy = top - hr
    d.ellipse([cx - hr, hy - hr, cx + hr, hy + hr], fill=skin)
    # 发
    d.pieslice([cx - hr, hy - hr - 4 * s, cx + hr, hy + hr], 180, 360, fill=hair)
    d.ellipse([cx - 4 * s, hy - hr - 8 * s, cx + 4 * s, hy - hr + 2 * s], fill=hair)  # 发髻
    # 眼
    d.rectangle([cx - 7 * s, hy - 2 * s, cx - 4 * s, hy + 1 * s], fill=hair)
    d.rectangle([cx + 4 * s, hy - 2 * s, cx + 7 * s, hy + 1 * s], fill=hair)


def draw_room(d, kind):
    # 顶菜单条
    d.rectangle([0, 0, W, TOPBAR_H], fill=(109, 155, 178))
    d.rectangle([0, TOPBAR_H, W, TOPBAR_H + 2], fill=GOLD_DK)
    d.text((14, 6), "城 内", font=font(18, True), fill=(20, 30, 40))
    for i, t in enumerate(["終了", "情報", "機能"]):
        d.text((W - 220 + i * 72, 7), t, font=font(15), fill=(20, 30, 40))

    # 墙
    wall = Image.new("RGB", (W, FLOOR_Y - TOPBAR_H), (110, 72, 36))
    wd = ImageDraw.Draw(wall)
    for y in range(0, FLOOR_Y - TOPBAR_H, 6):
        wd.line([(0, y), (W, y)], fill=(96, 60, 28), width=1)
    # 右侧纸障子
    wd.rectangle([W - 300, 40, W - 40, FLOOR_Y - 60], fill=PAPER, outline=WOOD_DK, width=6)
    for i in range(1, 4):
        wd.line([(W - 300 + i * 65, 40), (W - 300 + i * 65, FLOOR_Y - 60)], fill=WOOD_DK, width=3)
    wd.line([(W - 300, 40 + (FLOOR_Y - 100) // 2), (W - 40, 40 + (FLOOR_Y - 100) // 2)], fill=WOOD_DK, width=3)
    img_paste = wall
    d._image.paste(wall, (0, TOPBAR_H))

    # 中央蓝暖帘
    d.rectangle([W // 2 - 150, TOPBAR_H + 10, W // 2 + 150, TOPBAR_H + 130], fill=BLUE, outline=BLUE_DK, width=4)
    for i in range(1, 5):
        d.line([(W // 2 - 150 + i * 60, TOPBAR_H + 10), (W // 2 - 150 + i * 60, TOPBAR_H + 130)], fill=BLUE_DK, width=3)
    d.text((W // 2 - 40, TOPBAR_H + 50), "茶", font=font(40, True), fill=(245, 240, 220))

    # 地面
    if kind == "teahouse":
        fg, fgdk = TATAMI, TATAMI_DK
    else:
        fg, fgdk = (96, 64, 30), (70, 46, 22)
    d.rectangle([0, FLOOR_Y, W, H - DLG_H], fill=fg)
    # 木地板线
    for x in range(0, W, 70):
        d.line([(x, FLOOR_Y), (x - 40, H - DLG_H)], fill=fgdk, width=2)
    d.line([(0, FLOOR_Y), (W, FLOOR_Y)], fill=GOLD_DK, width=3)

    # 家具：道场=木刀架；茶室=茶柜+挂轴；酒馆=酒桶；宿屋=床
    if kind == "dojo":
        d.rectangle([120, FLOOR_Y - 150, 280, FLOOR_Y - 10], fill=WOOD, outline=WOOD_DK, width=4)
        for i in range(4):
            d.rectangle([140 + i * 34, FLOOR_Y - 190, 162 + i * 34, FLOOR_Y - 60], fill=(200, 170, 120), outline=WOOD_DK, width=2)
    elif kind == "teahouse":
        d.rectangle([120, FLOOR_Y - 120, 250, FLOOR_Y - 10], fill=WOOD, outline=WOOD_DK, width=4)
        d.rectangle([150, FLOOR_Y - 100, 220, FLOOR_Y - 30], fill=(60, 40, 20))
        d.rectangle([W - 360, FLOOR_Y - 200, W - 250, FLOOR_Y - 60], fill=PAPER, outline=WOOD_DK, width=5)
        d.text((W - 340, FLOOR_Y - 170), "和", font=font(28, True), fill=(40, 30, 20))
    elif kind == "tavern":
        for i in range(3):
            d.ellipse([140 + i * 70, FLOOR_Y - 90, 200 + i * 70, FLOOR_Y - 10], fill=(150, 100, 50), outline=WOOD_DK, width=3)
    elif kind == "inn":
        d.rectangle([120, FLOOR_Y - 70, 360, FLOOR_Y - 10], fill=(120, 90, 50), outline=WOOD_DK, width=4)

    # 角色：玩家(左) + NPC(右)
    draw_char(d, 360, FLOOR_Y + 150, 1.5, robe=(60, 90, 150), band=GOLD)       # 玩家蓝袍
    draw_char(d, 680, FLOOR_Y + 150, 1.5, robe=(150, 60, 60), band=(220, 200, 80))  # NPC 红袍

    # 底部对话框
    dy0 = H - DLG_H
    d.rectangle([0, dy0 - 4, W, dy0 - 2], fill=GOLD_DK)
    d.rectangle([16, dy0, W - 16, H - 12], fill=(18, 26, 48), outline=GOLD, width=3)
    # 头像框
    d.rectangle([28, dy0 + 12, 28 + 88, dy0 + 12 + 88], fill=(10, 16, 32), outline=GOLD, width=2)
    d.ellipse([28 + 24, dy0 + 24, 28 + 64, dy0 + 64], fill=(232, 200, 170))
    d.text((44, dy0 + 36), "N", font=font(30, True), fill=(40, 30, 20))
    # 名字条
    d.text((130, dy0 + 16), "武 将", font=font(18, True), fill=GOLD)
    # 对白
    d.text((130, dy0 + 48), "此處乃修行的好所在，閣下可願一試？", font=font(17), fill=TEXT)
    d.text((W - 120, H - 36), "▼ 繼續", font=font(14), fill=(180, 200, 220))


def main():
    for kind, out in [("teahouse", "assets/indoor_preview.png"),
                      ("dojo", "assets/indoor_preview_dojo.png")]:
        img = Image.new("RGB", (W, H), DARK)
        d = ImageDraw.Draw(img)
        draw_room(d, kind)
        img.save(out, "PNG", optimize=True)
        import os
        print(f"OK: {out} ({os.path.getsize(out)} bytes)  kind={kind}")


if __name__ == "__main__":
    main()
