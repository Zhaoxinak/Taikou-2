# -*- coding: utf-8 -*-
"""
生成 HD-2D 占位图（不调 ImageGen，零积分）。

太阁2 复刻的美术（695 张武将立绘 / 16 张单位 sprite / 地形材质等）尚未批量生成，
本项目用程序生成的「中性占位图」顶上，使所有引用美术的位置都能渲染，不阻塞复刻。
真实美术就位后，直接按同名文件替换 assets/sprites/{portraits,units,chips}/ 下对应图即可。

输出（均为 RGBA PNG，透明背景便于 HD-2D billboard）：
  assets/sprites/portraits/placeholder_portrait.png  512x640  武将立绘占位
  assets/sprites/units/placeholder_unit.png          256x256  单位 sprite 占位
  assets/sprites/chips/placeholder_chip.png           32x32   地形/UI 小图占位

纯标准库（zlib + struct）写 PNG，无第三方依赖。
"""
import os
import zlib
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # <工程根>
OUT_DIRS = {
    "portraits": os.path.join(ROOT, "assets", "sprites", "portraits"),
    "units": os.path.join(ROOT, "assets", "sprites", "units"),
    "chips": os.path.join(ROOT, "assets", "sprites", "chips"),
}


def write_png(path, w, h, buf):
    """buf: bytearray, 长度 w*h*4, RGBA8。filter=0(无) 逐行。"""
    def chunk(typ, data):
        c = typ + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)  # 8bit, color type 6 (RGBA)
    raw = bytearray()
    for y in range(h):
        raw.append(0)  # filter byte: none
        raw += buf[y * w * 4:(y + 1) * w * 4]
    idat = zlib.compress(bytes(raw), 9)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


class Img:
    def __init__(self, w, h, bg=(0, 0, 0, 0)):
        self.w = w
        self.h = h
        self.buf = bytearray(w * h * 4)
        for i in range(w * h):
            self.buf[i * 4:i * 4 + 4] = bytes(bg)

    def set(self, x, y, rgba):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 4
            self.buf[i:i + 4] = bytes(rgba)

    def fill_rect(self, x0, y0, x1, y1, rgba):
        for y in range(max(0, y0), min(self.h, y1)):
            for x in range(max(0, x0), min(self.w, x1)):
                self.set(x, y, rgba)

    def _disc(self, cx, cy, rr):
        for y in range(max(0, int(cy - rr)), min(self.h, int(cy + rr) + 1)):
            for x in range(max(0, int(cx - rr)), min(self.w, int(cx + rr) + 1)):
                dx, dy = x - cx, y - cy
                if dx * dx + dy * dy <= rr * rr:
                    yield x, y

    def fill_circle(self, cx, cy, rr, rgba):
        for x, y in self._disc(cx, cy, rr):
            self.set(x, y, rgba)

    def stroke_circle(self, cx, cy, rr, rgba, t=3):
        outer = self._disc(cx, cy, rr)
        for x, y in outer:
            inside = False
            for ox in range(-t, t + 1):
                for oy in range(-t, t + 1):
                    ddx, ddy = x + ox - cx, y + oy - cy
                    if ddx * ddx + ddy * ddy > (rr - t) * (rr - t):
                        inside = True
                        break
                if inside:
                    break
            if inside:
                self.set(x, y, rgba)

    def write(self, path):
        write_png(path, self.w, self.h, self.buf)


def make_portrait():
    """512x640 武将立绘占位：暗色卡 + 头部椭圆 + 肩身梯形 + 细边框。"""
    w, h = 512, 640
    im = Img(w, h, (26, 30, 42, 255))  # 暗板岩底
    # 顶部到底部的轻微竖向渐变（亮一点）
    for y in range(h):
        k = y / h
        r = int(26 + (40 - 26) * k)
        g = int(30 + (46 - 30) * k)
        b = int(42 + (60 - 42) * k)
        im.fill_rect(0, y, w, y + 1, (r, g, b, 255))
    # 细边框
    im.fill_rect(0, 0, w, 6, (90, 100, 130, 255))
    im.fill_rect(0, h - 6, w, h, (90, 100, 130, 255))
    im.fill_rect(0, 0, 6, h, (90, 100, 130, 255))
    im.fill_rect(w - 6, 0, w, h, (90, 100, 130, 255))
    # 头部椭圆
    im.fill_circle(256, 215, 92, (120, 132, 156, 255))
    # 肩身梯形（用矩形近似 + 两侧收窄）
    for y in range(330, h - 6):
        t = (y - 330) / (h - 6 - 330)
        half_w = int(150 + 90 * t)  # 向下变宽
        im.fill_rect(256 - half_w, y, 256 + half_w, y + 1, (96, 108, 132, 255))
    # 头盔顶饰（一小三角，暗示武将）
    for y in range(120, 170):
        half = int((y - 120) / 50 * 26)
        im.fill_rect(256 - half, y, 256 + half, y + 1, (150, 60, 60, 255))
    return im


def make_unit():
    """256x256 单位 sprite 占位：透明底 + 钢色圆 token + 头盔三角。"""
    w = h = 256
    im = Img(w, h, (0, 0, 0, 0))  # 透明
    im.fill_circle(128, 150, 84, (86, 98, 122, 255))   # 躯体 token
    im.stroke_circle(128, 150, 84, (150, 165, 190, 255), 4)
    # 头盔三角
    for y in range(58, 110):
        half = int((y - 58) / 52 * 34)
        im.fill_rect(128 - half, y, 128 + half, y + 1, (150, 60, 60, 255))
    # 中央小十字（军标记号）
    im.fill_rect(122, 140, 134, 162, (200, 200, 210, 255))
    im.fill_rect(118, 144, 138, 158, (200, 200, 210, 255))
    return im


def make_chip():
    """32x32 小图占位：中性灰块 + 角标。"""
    w = h = 32
    im = Img(w, h, (110, 110, 118, 255))
    im.fill_rect(0, 0, w, 2, (70, 70, 78, 255))
    im.fill_rect(0, h - 2, w, h, (70, 70, 78, 255))
    im.fill_rect(0, 0, 2, h, (70, 70, 78, 255))
    im.fill_rect(w - 2, 0, w, h, (70, 70, 78, 255))
    im.fill_rect(12, 12, 20, 20, (150, 150, 160, 255))
    return im


def main():
    for d in OUT_DIRS.values():
        os.makedirs(d, exist_ok=True)
    make_portrait().write(os.path.join(OUT_DIRS["portraits"], "placeholder_portrait.png"))
    make_unit().write(os.path.join(OUT_DIRS["units"], "placeholder_unit.png"))
    make_chip().write(os.path.join(OUT_DIRS["chips"], "placeholder_chip.png"))
    print("[ok] 占位图已生成:")
    for name, d in OUT_DIRS.items():
        print("     %s -> %s" % (name, d))


if __name__ == "__main__":
    main()
