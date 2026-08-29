"""
会议/宴席画面预览生成（#11 原版参照）
- 窗口标题栏 + 菜单条
- 左上对话框（立绘 + §名字§ + 对白）
- iso 室内：榻榻米+木地板+障子屏风+多角色分排
- 底部说明：スペースキーで次へ
"""
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 640, 400
ASSET_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
OUT = os.path.normpath(os.path.join(ASSET_DIR, "meeting_preview.png"))

# 调色（接近原版）
COL_BG_BLUE = (16, 32, 80)          # 底部蓝
COL_PATTERN = (8, 16, 48)            # 深蓝菱形纹
COL_PARCH = (250, 240, 210)         # 羊皮纸
COL_PARCH_DK = (220, 200, 160)      # 羊皮纸阴影
COL_BORDER = (40, 70, 40)           # 深绿边框
COL_GOLD = (200, 170, 70)           # 金色名字
COL_TEXT = (40, 30, 20)             # 深色字
COL_WOOD = (90, 55, 30)             # 木板色
COL_WOOD_LT = (130, 85, 50)         # 浅木板
COL_TATAMI = (90, 130, 80)          # 榻榻米绿
COL_TATAMI_DK = (70, 105, 60)       # 榻榻米暗
COL_SHOJI = (240, 230, 200)         # 障子纸
COL_SHOJI_GRID = (140, 100, 60)     # 障子木格
COL_KIMONO_BROWN = (110, 70, 40)    # 茶色服
COL_KIMONO_BLUE = (50, 75, 110)     # 蓝服
COL_KIMONO_GREEN = (60, 95, 65)     # 绿服
COL_SKIN = (220, 190, 150)          # 肤色
COL_HAIR_BLK = (30, 25, 20)         # 黑发
COL_HAIR_BRN = (50, 35, 20)         # 棕发


def load_font(size, bold=False):
    """尝试加载本地可用字体（win/mac/linux 通用兜底）"""
    candidates = [
        "C:/Windows/Fonts/msmincho.ttc",
        "C:/Windows/Fonts/MSMINCHO.TTC",
        "C:/Windows/Fonts/msgothic.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        "/System/Library/Fonts/ヒラギノ角 Pro W3.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


def make_canvas():
    img = Image.new("RGB", (W, H), COL_BG_BLUE)
    d = ImageDraw.Draw(img)
    return img, d


def draw_window_chrome(img, d):
    # 顶部浅蓝灰条（菜单条）
    d.rectangle([(0, 0), (W, 18)], fill=(232, 232, 232))
    d.text((8, 3), "太閤立志傳 II", font=load_font(12, True), fill=(20, 20, 20))
    d.text((W - 130, 3), "終了(X)  版本情報(V)", font=load_font(11), fill=(20, 20, 20))
    # 分隔线
    d.line([(0, 18), (W, 18)], fill=(160, 160, 160), width=1)


def draw_bottom_border(img, d):
    """底部深蓝菱形纹边框"""
    pattern_h = 28
    d.rectangle([(0, H - pattern_h), (W, H)], fill=COL_BG_BLUE)
    s = 8
    for y in range(H - pattern_h, H, s):
        for x in range(0, W, s):
            if ((x + y) // s) % 2 == 0:
                d.polygon(
                    [(x + s // 2, y), (x + s, y + s // 2),
                     (x + s // 2, y + s), (x, y + s // 2)],
                    fill=COL_PATTERN,
                )


def draw_floor_and_walls(img, d):
    """木地板 + 障子屏风（背景室内）"""
    # 障子屏风：右侧 + 顶部
    # 上半部：木墙
    wall_top = 24
    d.rectangle([(0, wall_top), (W, 100)], fill=(75, 50, 30))
    # 木墙横纹
    for y in range(wall_top, 100, 12):
        d.line([(0, y), (W, y)], fill=(60, 40, 22), width=1)

    # 障子屏风（右侧大块）
    shoji_x0, shoji_y0, shoji_w, shoji_h = 410, 24, 220, 100
    d.rectangle([(shoji_x0, shoji_y0), (shoji_x0 + shoji_w, shoji_y0 + shoji_h)],
                fill=COL_SHOJI)
    # 木格
    grid_n = 4
    for i in range(1, grid_n):
        x = shoji_x0 + i * (shoji_w // grid_n)
        d.line([(x, shoji_y0), (x, shoji_y0 + shoji_h)], fill=COL_SHOJI_GRID, width=1)
    for i in range(1, 3):
        y = shoji_y0 + i * (shoji_h // 3)
        d.line([(shoji_x0, y), (shoji_x0 + shoji_w, y)], fill=COL_SHOJI_GRID, width=1)
    # 外框
    d.rectangle([(shoji_x0, shoji_y0), (shoji_x0 + shoji_w, shoji_y0 + shoji_h)],
                outline=COL_SHOJI_GRID, width=2)
    # 障子下方小窗（床之间/架台）
    d.rectangle([(shoji_x0 + 5, shoji_y0 + shoji_h - 30),
                 (shoji_x0 + shoji_w - 5, shoji_y0 + shoji_h)],
                fill=(40, 25, 15))

    # 木地板（占下半）
    floor_y0 = 100
    d.rectangle([(0, floor_y0), (W, H - 28)], fill=COL_WOOD)
    # 木板纹（横线）
    for y in range(floor_y0, H - 28, 6):
        d.line([(0, y), (W, y)], fill=COL_WOOD_LT, width=1)
    # 竖缝
    for x in range(0, W, 40):
        d.line([(x, floor_y0), (x, H - 28)], fill=(60, 35, 18), width=1)


def draw_tatami(img, d):
    """中央榻榻米+上首主公位置"""
    # 绿色榻榻米（主位/主君席）
    tatami_x0, tatami_y0 = 220, 120
    tatami_w, tatami_h = 200, 60
    d.rectangle([(tatami_x0, tatami_y0), (tatami_x0 + tatami_w, tatami_y0 + tatami_h)],
                fill=COL_TATAMI)
    # 榻榻米边
    d.rectangle([(tatami_x0, tatami_y0), (tatami_x0 + tatami_w, tatami_y0 + tatami_h)],
                outline=COL_TATAMI_DK, width=2)
    # 榻榻米内格子
    cells = 4
    for i in range(1, cells):
        d.line([(tatami_x0 + i * (tatami_w // cells), tatami_y0),
                (tatami_x0 + i * (tatami_w // cells), tatami_y0 + tatami_h)],
               fill=COL_TATAMI_DK, width=1)

    # 正面台阶（主公坐的稍高位）
    step_y = tatami_y0 - 10
    d.rectangle([(tatami_x0 - 10, step_y), (tatami_x0 + tatami_w + 10, tatami_y0)],
                fill=(60, 40, 22))


def draw_chara_simple(d, cx, cy, color_kimono, color_kimono2, with_obi=None,
                      facing="front", size=1.0, headband_color=None):
    """画一个简化角色（iso 视角前/后）
    cx, cy: 中心底部坐标
    facing: front（面向镜头）/back（背向镜头）
    size: 缩放
    """
    s = size
    # 身体（坐姿）：梯形
    body_w = int(22 * s)
    body_h = int(28 * s)
    body_y = cy - body_h
    # 身体用两个色块（上衣+下裙）
    d.polygon(
        [(cx - body_w // 2, body_y + body_h // 3),
         (cx + body_w // 2, body_y + body_h // 3),
         (cx + body_w // 2 - 2, body_y + body_h),
         (cx - body_w // 2 + 2, body_y + body_h)],
        fill=color_kimono,
    )
    # 腰带 obi
    obi_h = int(4 * s)
    d.rectangle([(cx - body_w // 2 + 1, body_y + body_h * 2 // 3 - obi_h // 2),
                 (cx + body_w // 2 - 1, body_y + body_h * 2 // 3 + obi_h // 2)],
                fill=with_obi or (180, 130, 60))
    # 头（圆形/椭圆）
    head_r = int(10 * s)
    head_cx = cx
    head_cy = body_y + head_r // 2
    d.ellipse([(head_cx - head_r, head_cy - head_r),
               (head_cx + head_r, head_cy + head_r)],
              fill=COL_SKIN)
    # 发髻/头发
    hair_h = int(8 * s)
    d.chord([(head_cx - head_r, head_cy - head_r),
             (head_cx + head_r, head_cy + head_r - 1)],
            start=200, end=340, fill=COL_HAIR_BLK)
    # 头顶发髻丸
    d.ellipse([(head_cx - 3, head_cy - head_r - 5),
               (head_cx + 6, head_cy - head_r + 1)],
              fill=COL_HAIR_BLK)
    # 头巾
    if headband_color:
        d.rectangle([(head_cx - head_r, head_cy - head_r // 2 - 1),
                     (head_cx + head_r, head_cy - head_r // 2 + 2)],
                    fill=headband_color)
    # 背向时不画五官
    if facing == "front":
        # 眼睛
        eye_y = head_cy + 1
        d.ellipse([(head_cx - 5, eye_y - 1), (head_cx - 3, eye_y + 1)], fill=(20, 15, 10))
        d.ellipse([(head_cx + 3, eye_y - 1), (head_cx + 5, eye_y + 1)], fill=(20, 15, 10))
        # 胡须（武将）
        if with_obi and with_obi[0] > 150:  # obi 偏暖=武将
            d.line([(head_cx - 4, head_cy + 5), (head_cx - 2, head_cy + 7)], fill=COL_HAIR_BRN, width=1)
            d.line([(head_cx + 2, head_cy + 5), (head_cx + 4, head_cy + 7)], fill=COL_HAIR_BRN, width=1)


def draw_meeting_formation(img, d):
    """会议排位：
       上首主公（绿榻上） + 左右两武将 + 前景后排侍坐
    """
    # 上首主公（居中坐高位，面朝镜头）
    lord_cx, lord_cy = 320, 130
    draw_chara_simple(d, lord_cx, lord_cy, COL_KIMONO_BLUE, COL_KIMONO_GREEN,
                      with_obi=(80, 50, 30), facing="front", size=1.0,
                      headband_color=None)

    # 左右两武将（主公两侧，tach 上跪坐）
    left_war_cx, left_war_cy = 250, 170
    right_war_cx, right_war_cy = 390, 170
    draw_chara_simple(d, left_war_cx, left_war_cy, COL_KIMONO_BROWN, COL_KIMONO_BROWN,
                      with_obi=(60, 35, 20), facing="front", size=0.95)
    draw_chara_simple(d, right_war_cx, right_war_cy, COL_KIMONO_BROWN, COL_KIMONO_BROWN,
                      with_obi=(60, 35, 20), facing="front", size=0.95)

    # 中排：8 个侍坐（背向镜头）
    mid_y = 220
    mid_xs = [80, 130, 180, 230, 320, 410, 460, 510, 560]
    # 实际原版 8 个
    mid_xs = [60, 110, 165, 215, 425, 475, 530, 580]
    colors = [COL_KIMONO_BROWN, COL_KIMONO_BLUE, COL_KIMONO_GREEN,
              COL_KIMONO_BROWN, COL_KIMONO_BROWN, COL_KIMONO_BLUE,
              COL_KIMONO_GREEN, COL_KIMONO_BROWN]
    for x, col in zip(mid_xs, colors):
        draw_chara_simple(d, x, mid_y, col, col,
                          with_obi=(100, 70, 40), facing="back", size=0.85)

    # 前排：3 个侍坐（面向镜头）
    front_y = 290
    front_xs = [180, 320, 460]
    front_cols = [COL_KIMONO_BLUE, COL_KIMONO_BROWN, COL_KIMONO_GREEN]
    for x, col in zip(front_xs, front_cols):
        draw_chara_simple(d, x, front_y, col, col,
                          with_obi=(120, 80, 50), facing="front", size=0.9)


def draw_dialogue_box(img, d):
    """左上对话窗：立绘 + 名字 + 对白"""
    box_x, box_y = 16, 30
    box_w, box_h = 290, 110
    # 外边框（深绿）
    d.rectangle([(box_x - 2, box_y - 2), (box_x + box_w + 2, box_y + box_h + 2)],
                fill=COL_BORDER)
    # 羊皮纸底
    d.rectangle([(box_x, box_y), (box_x + box_w, box_y + box_h)], fill=COL_PARCH)
    # 内边框装饰
    d.rectangle([(box_x + 4, box_y + 4), (box_x + box_w - 4, box_y + box_h - 4)],
                outline=COL_PARCH_DK, width=1)

    # 左侧立绘框
    portrait_w = 78
    portrait_h = box_h - 12
    p_x0 = box_x + 6
    p_y0 = box_y + 6
    d.rectangle([(p_x0, p_y0), (p_x0 + portrait_w, p_y0 + portrait_h)],
                fill=(235, 220, 180))
    d.rectangle([(p_x0, p_y0), (p_x0 + portrait_w, p_y0 + portrait_h)],
                outline=(160, 130, 80), width=1)

    # 立绘占位（武将面像：黑发+头巾+胡须）
    pcx, pcy = p_x0 + portrait_w // 2, p_y0 + portrait_h // 2
    # 头
    head_r = 18
    d.ellipse([(pcx - head_r, pcy - head_r), (pcx + head_r, pcy + head_r)],
              fill=COL_SKIN)
    # 发髻
    d.ellipse([(pcx - 6, pcy - head_r - 3), (pcx + 8, pcy - head_r + 5)],
              fill=COL_HAIR_BLK)
    # 蓝头巾（横带）
    d.rectangle([(pcx - head_r, pcy - 4), (pcx + head_r, pcy + 2)],
                fill=(50, 80, 140))
    # 眼睛
    d.ellipse([(pcx - 7, pcy + 4), (pcx - 4, pcy + 7)], fill=(20, 15, 10))
    d.ellipse([(pcx + 4, pcy + 4), (pcx + 7, pcy + 7)], fill=(20, 15, 10))
    # 嘴/胡须
    d.line([(pcx - 6, pcy + 13), (pcx, pcy + 15)], fill=COL_HAIR_BRN, width=1)
    d.line([(pcx, pcy + 15), (pcx + 6, pcy + 13)], fill=COL_HAIR_BRN, width=1)

    # 右侧文本
    tx = p_x0 + portrait_w + 10
    tw = box_w - portrait_w - 18
    # 名字条（金色 § 名字 §）
    f_name = load_font(13, True)
    f_text = load_font(12)
    name = "§  丹羽長秀  §"
    # 居中显示
    name_w = d.textlength(name, font=f_name)
    d.text(((tx + (tw - name_w) / 2), box_y + 8), name, font=f_name, fill=COL_GOLD)

    # 对白（多行）
    text = "不要再犹豫了！\n现在只有发动战争，\n才能解决问题。"
    lines = text.split("\n")
    for i, line in enumerate(lines):
        d.text((tx + 4, box_y + 30 + i * 18), line, font=f_text, fill=COL_TEXT)

    # 右下角小三角（翻页指示）
    d.polygon([(box_x + box_w - 14, box_y + box_h - 14),
               (box_x + box_w - 6, box_y + box_h - 14),
               (box_x + box_w - 10, box_y + box_h - 6)], fill=COL_GOLD)


def draw_bottom_hint(img, d):
    """底部操作提示"""
    f = load_font(11)
    d.text((12, H - 22), "スペース：次へ    ESC：会議を閉じる",
           font=f, fill=(220, 220, 230))


def main():
    img, d = make_canvas()
    draw_window_chrome(img, d)
    draw_floor_and_walls(img, d)
    draw_tatami(img, d)
    draw_meeting_formation(img, d)
    draw_dialogue_box(img, d)
    draw_bottom_hint(img, d)
    draw_bottom_border(img, d)
    img.save(OUT, "PNG", optimize=True)
    print(f"OK: {OUT}  ({os.path.getsize(OUT)} bytes)")


if __name__ == "__main__":
    main()
