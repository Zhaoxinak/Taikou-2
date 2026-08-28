"""用真实原版素材生成城下町『纯场景』背景（1024x640），供 CastleTown.gd 加载。

只包含场景本体（真实 TOWNCHIP 地面瓦片 + 真实 HBCHAR 武将精灵 + 真实建筑瓦片），
UI 框架（顶条/右面板/底栏/日期）由 Godot 端 CastleTown.gd 原生绘制叠加。

输出：
  assets/real_townchip.png  (272x336 真实瓦片总表)
  assets/real_hbchar.png    (256x384 真实精灵总表)
  assets/castle_town_real.png (1024x640 纯场景，真素材)
"""
import sys
sys.path.insert(0, "scripts")
from real_assets import decode_townchip, decode_hbchar, decode_ega_sprite
from PIL import Image, ImageDraw, ImageFont

ASSETS = "assets"
W, H = 1024, 640

timg, tn, t_raw = decode_townchip()
himg, hn, hb_raw = decode_hbchar()

def get_tile(timg, ti, cols=17, tw=16, th=16):
    tx = (ti % cols) * tw
    ty = (ti // cols) * th
    return timg.crop((tx, ty, tx + tw, ty + th))

def get_sprite_transparent(index, scale=3):
    sp = decode_ega_sprite(hb_raw, index)
    px = sp.load()
    out = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    opx = out.load()
    for y in range(16):
        for x in range(16):
            r, g, b, a = px[x, y]
            if a > 0 and not (r < 16 and g < 16 and b < 16):  # 索引0(纯黑)=透明
                opx[x, y] = (r, g, b, 255)
    if scale != 1:
        out = out.resize((16 * scale, 16 * scale), Image.NEAREST)
    return out

# 导出真实总表
timg.save(f"{ASSETS}/real_townchip.png")
himg.save(f"{ASSETS}/real_hbchar.png")
print("导出 real_townchip.png / real_hbchar.png")

# 背景（深色打底，瓦片铺不满处不突兀）
img = Image.new("RGBA", (W, H), (10, 14, 24, 255))

# ---- 地面：真实 TOWNCHIP 地面瓦片(0-9) 平铺 ----
ground_ids = list(range(0, 10))
gw, gh = 16, 16
cols_t = W // gw
rows_t = H // gh
for ry in range(rows_t):
    for cx in range(cols_t):
        tid = ground_ids[(cx * 3 + ry * 5) % len(ground_ids)]
        img.paste(get_tile(timg, tid), (cx * gw, ry * gh))

# ---- 建筑：真实建筑瓦片(10-25) 摆几栋 ----
build_ids = list(range(10, 26))
spots = [(120, 120), (380, 90), (640, 150), (240, 360), (700, 380), (480, 300)]
for i, (bx, by) in enumerate(spots):
    t = get_tile(timg, build_ids[i % len(build_ids)])
    img.paste(t, (bx, by))

# ---- 人物：真实 HBCHAR 精灵 ----
# 主角（放大4倍，靠前居中）
player = get_sprite_transparent(0, 4)
img.paste(player, (470, 430), player)
# NPC（放大3倍，散布）
npcs = [(44, 250, 3), (300, 200, 9), (560, 470, 12), (760, 260, 21), (180, 500, 30)]
for nx, ny, fi in npcs:
    s = get_sprite_transparent(fi, 3)
    img.paste(s, (nx, ny), s)

img.convert("RGB").save(f"{ASSETS}/castle_town_real.png", "PNG")
print("导出 castle_town_real.png", img.size)
