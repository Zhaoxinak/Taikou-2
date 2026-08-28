"""城下町 iso 画面预览 —— 还原原版截图 #10（城堡町 + 主角面板）。

输出 assets/castle_town_preview.png (640×400，贴近原版分辨率)。
这是"完美复刻"的视觉基准：iso 木地板 + 木屋/围栏/矮松 + NPC +
右侧绿底人物面板 + 底部 5 图标 + 日期条 + 顶部菜单条。
"""
from PIL import Image, ImageDraw, ImageFont

W, H = 640, 400
img = Image.new("RGB", (W, H), (8, 12, 24))
d = ImageDraw.Draw(img)

try:
    fp = "C:/Windows/Fonts/simhei.ttf"
    font = ImageFont.truetype(fp, 13)
    font_s = ImageFont.truetype(fp, 10)
    font_b = ImageFont.truetype(fp, 16)
    font_bb = ImageFont.truetype(fp, 18)
except Exception:
    font = font_s = font_b = font_bb = ImageFont.load_default()

# ---- 配色（KOEI 1995 风）----
GOLD = (212, 168, 55)
GOLD_D = (138, 106, 26)
GOLD_L = (245, 216, 120)
WOOD = (58, 36, 16)
PANEL = (26, 37, 64)
PANEL_L = (46, 72, 112)
GREEN = (28, 104, 54)
GREEN_D = (12, 54, 28)
GREEN_L = (60, 150, 90)
SKY = (62, 92, 132)          # 顶部菜单条浅蓝
FLOOR = (206, 164, 92)       # 木地板顶
FLOOR_D = (150, 112, 56)     # 木地板暗
FLOOR_L = (224, 188, 120)    # 木地板亮
WALL = (120, 80, 42)         # 木墙
WALL_L = (160, 110, 60)
ROOF = (86, 96, 122)         # 瓦顶蓝灰
ROOF_D = (56, 64, 86)


def iso(cx, cy):
    """iso 投影：tile 中心 -> 屏幕坐标"""
    return (OX + (cx - cy) * TW // 2, OY + (cx + cy) * TH // 2)


TW, TH = 32, 16
OX, OY = 212, 70
COLS, ROWS = 13, 10


def diamond(x, y, fill, outline, lw=1):
    pts = [(x, y), (x + TW // 2, y + TH // 2), (x, y + TH), (x - TW // 2, y + TH // 2)]
    d.polygon(pts, fill=fill, outline=outline)


def cube(c, r, h, wall_col=WALL, top_col=FLOOR_L, roof=False, roof_col=ROOF):
    """在 tile(c,r) 上画 2.5D 立方体（含可选屋顶）"""
    tx, ty = iso(c, r)
    # 顶面（抬高 h）
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
        # 屋顶：更大菱形抬更高 + 斜侧面
        rh = h + 14
        rtop = [(tx, ty - rh), (tx + TW // 2 + 4, ty + TH // 2 - rh + 7),
                (tx, ty + TH - rh), (tx - TW // 2 - 4, ty + TH // 2 - rh + 7)]
        rleft = [(tx - TW // 2 - 4, ty + TH // 2 - rh + 7), (tx, ty + TH - rh),
                 (tx, ty + TH - h), (tx - TW // 2, ty + TH // 2 - h)]
        rright = [(tx, ty + TH - rh), (tx + TW // 2 + 4, ty + TH // 2 - rh + 7),
                  (tx + TW // 2, ty + TH // 2 - h), (tx, ty + TH - h)]
        d.polygon(rleft, fill=(int(roof_col[0] * 0.7), int(roof_col[1] * 0.7), int(roof_col[2] * 0.7)))
        d.polygon(rright, fill=roof_col)
        d.polygon(rtop, fill=(int(roof_col[0] * 1.15), int(roof_col[1] * 1.15), int(roof_col[2] * 1.15)))


def pine(c, r, scale=1.0):
    """矮松树：绿色三角堆"""
    tx, ty = iso(c, r)
    h = int(26 * scale)
    w = int(10 * scale)
    layers = 3
    for i in range(layers):
        yy = ty - i * (h // layers) - (h // layers)
        d.polygon([(tx, yy), (tx - w, yy + h // layers + 6), (tx + w, yy + h // layers + 6)],
                  fill=(20 + i * 6, 90 + i * 14, 45 + i * 8))
    # 树干
    d.rectangle([(tx - 2, ty - 2), (tx + 2, ty + 6)], fill=(90, 60, 30))


def npc(c, r, body=(240, 240, 245), hair=(40, 30, 20)):
    """白色 NPC（主角/伙伴）：圆头 + 身体"""
    tx, ty = iso(c, r)
    # 身体（梯形白袍）
    d.polygon([(tx - 8, ty + 2), (tx + 8, ty + 2), (tx + 5, ty - 18), (tx - 5, ty - 18)],
              fill=body)
    # 下裳（深蓝）
    d.polygon([(tx - 8, ty + 2), (tx + 8, ty + 2), (tx + 6, ty + 10), (tx - 6, ty + 10)],
              fill=(40, 60, 110))
    # 头
    d.ellipse([(tx - 6, ty - 30), (tx + 6, ty - 18)], fill=(235, 200, 170))
    # 发
    d.pieslice([(tx - 6, ty - 30), (tx + 6, ty - 18)], 180, 360, fill=hair)


# ============ 1. 顶部菜单条 ============
d.rectangle([(0, 0), (W, 22)], fill=SKY)
d.line([(0, 22), (W, 22)], fill=GOLD_D, width=1)
d.text((8, 5), "結束", fill=(235, 240, 255), font=font_s)
d.text((W - 64, 5), "版本情報", fill=(235, 240, 255), font=font_s)

# ============ 2. iso 木地板 ============
# 从后往前画（r+c 小者后画，保证遮挡正确）
for s in range(0, COLS + ROWS):
    for c in range(COLS):
        r = s - c
        if r < 0 or r >= ROWS:
            continue
        x, y = iso(c, r)
        # 棋盘深浅
        base = FLOOR if ((c + r) % 2 == 0) else FLOOR_D
        diamond(x, y, base, (110, 80, 40))
        # 木纹横线
        d.line([(x - TW // 2 + 2, y + TH // 2), (x, y + TH - 1)], fill=(120, 90, 50), width=1)
        d.line([(x, y + 1), (x + TW // 2 - 2, y + TH // 2)], fill=(120, 90, 50), width=1)

# ============ 3. 建筑 / 围栏 / 松树 / NPC ============
# 木屋 1（带屋顶，蓝瓦）
cube(2, 1, 16, roof=True)
# 木屋 2
cube(9, 2, 14, roof=True, roof_col=(110, 80, 50))  # 茅草顶
# 围栏（矮立方排）
for i in range(4):
    cube(5 + i, 6, 8, wall_col=(150, 110, 60), top_col=(180, 140, 90))
# 中央大榻（白被子）—— 用一个矮亮立方
cube(6, 4, 10, wall_col=(220, 220, 225), top_col=(235, 235, 240))
# 蓝门（小立方，蓝色顶）
cube(3, 7, 18, wall_col=(90, 120, 160), top_col=(70, 100, 150))
# 矮松
pine(10, 6, 1.0)
pine(1, 8, 0.8)
pine(11, 8, 0.9)
# NPC（主角，居中偏下）
npc(6, 8)
# 第二个 NPC（伙伴，白衣）
npc(8, 7, body=(230, 225, 210), hair=(30, 25, 15))

# ============ 4. 右侧绿底人物面板 ============
PX0, PY0, PX1, PY1 = 432, 24, 632, 348
d.rectangle([(PX0, PY0), (PX1, PY1)], fill=GREEN, outline=GREEN_D)
d.rectangle([(PX0 + 3, PY0 + 3), (PX1 - 3, PY1 - 3)], outline=GOLD, width=1)
# 头像圆框
ax, ay, ar = 560, 70, 30
d.ellipse([(ax - ar, ay - ar), (ax + ar, ay + ar)], fill=(20, 70, 40), outline=GOLD_L)
# 脸
d.ellipse([(ax - 22, ay - 24), (ax + 22, ay + 20)], fill=(235, 200, 170))
d.rectangle([(ax - 22, ay - 6), (ax + 22, ay + 4)], fill=(40, 30, 20))  # 眼带
# 名字 + 官职
d.text((PX0 + 14, 36), "木下藤吉郎", fill=GOLD_L, font=font_b)
d.text((PX0 + 14, 110), "織田家步兵頭", fill=(220, 230, 220), font=font_s)
# 状态行
lines = [
    ("體力", "100 / 100", (255, 230, 120)),
    ("所持金", "1貫 000文", (255, 230, 120)),
    ("信賴度", "100 / 500", (255, 230, 120)),
    ("統禦力", "100", (200, 230, 200)),
    ("武  力", "100", (200, 230, 200)),
    ("內政力", "42", (200, 230, 200)),
    ("外交力", "28", (200, 230, 200)),
    ("魅  力", "31", (200, 230, 200)),
]
yy = 134
for k, v, col in lines:
    d.text((PX0 + 14, yy), k, fill=(200, 225, 200), font=font_s)
    d.text((PX0 + 110, yy), v, fill=col, font=font_s)
    yy += 20
# 任务 / 随从 按钮
d.rectangle([(PX0 + 14, 312), (PX0 + 100, 340)], fill=GREEN_L, outline=GOLD)
d.rectangle([(PX1 - 100, 312), (PX1 - 14, 340)], fill=GREEN_L, outline=GOLD)
d.text((PX0 + 40, 320), "任務", fill=(10, 40, 20), font=font_s)
d.text((PX1 - 74, 320), "隨從", fill=(10, 40, 20), font=font_s)
# 滚动条
d.rectangle([(PX1 - 12, PY0 + 6), (PX1 - 6, PY1 - 6)], fill=(20, 60, 35), outline=GREEN_D)
d.rectangle([(PX1 - 11, PY0 + 40), (PX1 - 7, PY0 + 110)], fill=GREEN_L)

# ============ 5. 日期条（金菱形花纹）============
DY0, DY1 = 350, 368
d.rectangle([(0, DY0), (W, DY1)], fill=(20, 30, 55))
# 菱形花纹
for x in range(0, W, 24):
    d.polygon([(x + 12, DY0 + 4), (x + 20, DY0 + 9), (x + 12, DY0 + 14), (x + 4, DY0 + 9)],
              fill=GOLD_D, outline=None)
d.text((W // 2 - 70, DY0 + 3), "1560年 5月21日", fill=GOLD_L, font=font_b)

# ============ 6. 底部 5 图标 ============
BY0, BY1 = 370, 400
icons = ["調查", "交涉", "交戰", "情報", "機能"]
iw = W // 5
for i, name in enumerate(icons):
    x0 = i * iw
    d.rectangle([(x0 + 2, BY0 + 2), (x0 + iw - 2, BY1 - 2)], fill=WOOD, outline=GOLD)
    d.rectangle([(x0 + 4, BY0 + 4), (x0 + iw - 4, BY1 - 4)], outline=GOLD_D, width=1)
    tw = d.textlength(name, font=font)
    d.text((x0 + (iw - tw) / 2, BY0 + 9), name, fill=GOLD_L, font=font)

# ============ 7. 左下角小按钮（原版 简体/講教）============
d.rectangle([(8, DY0 - 22), (70, DY0 - 4)], fill=PANEL_L, outline=GOLD)
d.text((18, DY0 - 19), "簡體", fill=GOLD_L, font=font_s)
d.rectangle([(78, DY0 - 22), (150, DY0 - 4)], fill=PANEL_L, outline=GOLD)
d.text((88, DY0 - 19), "講教", fill=GOLD_L, font=font_s)
# 中下 "指定目的地"
d.rectangle([(W // 2 - 70, DY0 - 22), (W // 2 + 70, DY0 - 4)], fill=PANEL_L, outline=GOLD)
d.text((W // 2 - 50, DY0 - 19), "指定目的地", fill=GOLD_L, font=font_s)

img.save("F:/Games/Taikou 2/assets/castle_town_preview.png", optimize=True)
print("castle_town_preview.png ->", W, "x", H)
