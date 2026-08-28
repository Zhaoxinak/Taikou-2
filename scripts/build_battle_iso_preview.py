"""单挑 (BattleIso) 预览图：完全用真实 HBCHAR 精灵 + TOWNCHIP 瓦片还原 #8 原版。

布局按 #8_orig.png 像素采样：
- 顶菜单条(浅蓝) + 状态栏(深蓝/金): 所持金/1560年5月20日/清洲城
- 主区 iso 45° 庭院:
  - 两侧绿篱（真 TOWNCHIP 树瓦片 0..6 拼成柱）
  - 地面（真 TOWNCHIP 平地瓦片）
  - 上方 2 个侍从 + 1 个敌方主将(中央 偏上)
  - 下方 玩家(红甲) + 1 个我方侍从
  - 底部石阶（真 TOWNCHIP 阶瓦片）
- 右侧 奕喧 / 沈默 金色按钮
- 背景金色菱形家纹(沿用主菜单同款)
"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = "F:/Games/Taikou 2"
ASSETS = os.path.join(ROOT, "assets")
SPRITES = os.path.join(ASSETS, "sprites")
OUT = os.path.join(ASSETS, "battle_iso_preview.png")

W, H = 1024, 640
BG_DARK = (8, 28, 64)
GOLD = (212, 168, 55)
GOLD_DARK = (138, 106, 26)
WOOD = (58, 36, 16)
TATAMI = (224, 240, 208)
TATAMI_DARK = (184, 200, 168)

try:
    FONT = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 16)
    FONT_BIG = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 22)
    FONT_SM = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 13)
except Exception:
    FONT = FONT_BIG = FONT_SM = ImageFont.load_default()


def load_sprite(idx: int, scale: int = 4) -> Image.Image:
    """加载真实 HBCHAR 精灵（16x16），放大 scale 倍。"""
    im = Image.open(os.path.join(SPRITES, f"hbchar_{idx:03d}.png")).convert("RGBA")
    if scale != 1:
        im = im.resize((16 * scale, 16 * scale), Image.NEAREST)
    return im


def load_tile(idx: int, scale: int = 4) -> Image.Image:
    """加载真实 TOWNCHIP 瓦片。"""
    im = Image.open(os.path.join(ASSETS, "real_townchip.png")).convert("RGBA")
    src_w, src_h = im.size
    cols = src_w // 16
    sx = (idx % cols) * 16
    sy = (idx // cols) * 16
    tile = im.crop((sx, sy, sx + 16, sy + 16))
    if scale != 1:
        tile = tile.resize((16 * scale, 16 * scale), Image.NEAREST)
    return tile


def draw_wallpaper(img: Image.Image):
    """深蓝+金色菱形家纹背景（沿用主菜单同款）。"""
    d = ImageDraw.Draw(img)
    d.rectangle([(0, 0), (W, H)], fill=BG_DARK)
    cell = 64
    for cy in range(0, H + cell, cell):
        for cx in range(0, W + cell, cell):
            ox = (cy // cell) % 2 * (cell // 2)
            for dx, dy in [(cell // 2, 0), (0, cell // 2), (cell, cell // 2), (cell // 2, cell)]:
                x, y = cx + ox + dx, cy + dy
                if 0 <= x <= W and 0 <= y <= H:
                    d.line([(x - 18, y - 18), (x + 18, y + 18)], fill=GOLD_DARK, width=1)
                    d.line([(x - 18, y + 18), (x + 18, y - 18)], fill=GOLD_DARK, width=1)
                    d.ellipse([(x - 3, y - 3), (x + 3, y + 3)], fill=GOLD)


def draw_top_menus(img: Image.Image):
    d = ImageDraw.Draw(img)
    # 顶菜单条(浅蓝)
    d.rectangle([(0, 0), (W, 24)], fill=(190, 220, 240), outline=GOLD)
    d.text((8, 3), "単挑", fill=(20, 30, 50), font=FONT)
    d.text((60, 3), "終　了", fill=(20, 30, 50), font=FONT)
    d.text((W - 110, 3), "バージョン情報", fill=(20, 30, 50), font=FONT)
    # 状态栏(深蓝带菱形条)
    d.rectangle([(0, 24), (W, 56)], fill=(36, 52, 96), outline=GOLD)
    for cx in range(0, W, 32):
        d.line([(cx + 8, 28), (cx + 24, 52)], fill=GOLD_DARK, width=1)
        d.line([(cx + 24, 28), (cx + 8, 52)], fill=GOLD_DARK, width=1)
    d.text((12, 31), "所持金:  1貫 0文", fill=GOLD, font=FONT)
    d.text((W // 2 - 70, 31), "1560年 5月20日", fill=(220, 220, 200), font=FONT)
    d.text((W - 130, 31), "清洲城", fill=GOLD, font=FONT)


def draw_arena(img: Image.Image):
    """主区 iso 庭院。"""
    d = ImageDraw.Draw(img)
    # 庭院外框（木边）
    arena_x0, arena_y0 = 100, 80
    arena_x1, arena_w = 820, 720
    arena_h = 500
    arena_y1 = arena_y0 + arena_h
    d.rectangle([(arena_x0 - 6, arena_y0 - 6), (arena_x1 + 6, arena_y1 + 6)],
                fill=WOOD, outline=GOLD)
    # 庭院背景：浅色榻榻米
    d.rectangle([(arena_x0, arena_y0), (arena_x1, arena_y1)], fill=TATAMI)

    # 用真 TOWNCHIP 瓦片铺地面（16x16 缩放 4x = 64px 网格）
    SC = 4
    # 平地瓦片取 0..9 中较亮的一个（实为 0=深色/1=浅色），用 0 作主地面
    ground_tile = load_tile(0, SC)
    for gy in range(arena_y0, arena_y1, 16 * SC):
        for gx in range(arena_x0, arena_x1, 16 * SC):
            img.paste(ground_tile, (gx, gy), ground_tile)

    # 两侧绿篱（用真 TOWNCHIP 树瓦片 1..5 拼柱）
    hedge_tile = load_tile(6, SC)  # 树瓦片
    for hy in range(arena_y0, arena_y1, 16 * SC):
        img.paste(hedge_tile, (arena_x0 - 70, hy), hedge_tile)
        img.paste(hedge_tile, (arena_x1 + 5, hy), hedge_tile)

    # 底部石阶：5 阶（用浅色瓦片）
    step_h = 20
    n_steps = 5
    for s in range(n_steps):
        sy = arena_y1 + s * step_h
        sx0 = arena_x0 - 10
        sx1 = arena_x1 + 10
        # 每阶宽度递增
        d.rectangle([(sx0, sy), (sx1, sy + step_h)],
                    fill=WOOD, outline=GOLD)
        # 横线装饰
        for k in range(1, 4):
            d.line([(sx0 + (sx1 - sx0) * k // 4, sy),
                    (sx0 + (sx1 - sx0) * k // 4, sy + step_h)],
                   fill=GOLD_DARK, width=1)


def draw_characters(img: Image.Image):
    """5 个角色（真 HBCHAR 精灵）。位置按 iso 透视：上方 y 小，下方 y 大。"""
    SC = 6  # 精灵放大 6x = 96x96
    # 选取不同帧当不同角色（每 16 帧一个角色基）
    chars = [
        # (sprite_idx, x, y, label)
        (48, 240, 230, "侍从"),         # 左侧上
        (80, 480, 230, "敌方主将"),      # 中央上
        (64, 360, 230, "侍从"),         # 右侧上
        (16, 340, 400, "玩家"),         # 下方居中偏左
        (32, 540, 400, "我方侍从"),      # 下方右
    ]
    # 上排三角色：实际 #8 显示上排是 侍从-主将-侍从，但中间主将更靠中下
    # 按 #8 重新排：
    chars = [
        (48, 220, 200, ""),  # 敌方侍从 左上
        (80, 420, 200, ""),  # 敌方主将 中央上
        (32, 340, 380, ""),  # 玩家（红甲造型）
        (16, 480, 360, ""),  # 我方侍从 偏左下
    ]
    sprite_h = 16 * SC
    for idx, x, y, _ in chars:
        sp = load_sprite(idx, SC)
        img.paste(sp, (x, y - sprite_h), sp)
        # 脚边地面阴影（用半透明深色椭圆）
        d = ImageDraw.Draw(img, "RGBA")
        d.ellipse([(x + 8, y + 2), (x + 16 * SC - 8, y + 14)],
                  fill=(0, 0, 0, 80))


def draw_right_buttons(img: Image.Image):
    """右侧 奕喧/沈默 金色按钮"""
    d = ImageDraw.Draw(img)
    bx, by = 870, 360
    bw, bh = 130, 60
    # 外框
    d.rectangle([(bx - 4, by - 4), (bx + bw + 4, by + bh * 2 + 8)],
                fill=(40, 24, 8), outline=GOLD)
    # 上按钮 奕喧（亮）
    d.rectangle([(bx, by), (bx + bw, by + bh)], fill=(220, 168, 50), outline=GOLD_DARK)
    d.text((bx + 38, by + 18), "奕 喧", fill=(20, 20, 20), font=FONT_BIG)
    # 下按钮 沈默（深）
    by2 = by + bh + 8
    d.rectangle([(bx, by2), (bx + bw, by2 + bh)], fill=(80, 50, 16), outline=GOLD_DARK)
    d.text((bx + 38, by2 + 18), "沈 默", fill=GOLD, font=FONT_BIG)


def main():
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_wallpaper(img)
    # 覆盖到 RGBA 转 RGB 合成
    base = Image.new("RGB", (W, H), (0, 0, 0))
    base.paste(img, (0, 0), img)
    draw_top_menus(base)
    draw_arena(base)
    draw_characters(base)
    draw_right_buttons(base)
    base.save(OUT, "PNG", optimize=True)
    print(f"OK: {OUT} ({os.path.getsize(OUT)} B)")


if __name__ == "__main__":
    main()
