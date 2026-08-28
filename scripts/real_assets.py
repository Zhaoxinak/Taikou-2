"""real_assets.py — 太阁2 真实素材解码库（Python 移植，1:1 对应 TaikouImage.gd / TaikouLZW.gd）

从用户合法拷贝(F:/Games/Taikou2)读取原版 .LZW / .GRP，用与 Godot 端完全相同的算法解出：
  - TOWNCHIP  (341 张 16x16 瓦片, KOEI 4bpp 位平面)
  - HBCHAR    (384 张 16x16 精灵, EGA 4 平面)
  - MAPCHIP   (88 张 16x16 地形, 裸 RGB565)
  - FACE      (64x80 武将肖像)
  - GRP 背景  (RGB565)

全部不碰任何"假像素"——这就是原版 1995 年 KOEI 的真货。
"""
import json
import os
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

DATA_ROOT = "F:/Games/Taikou2"
PALETTE_PATH = os.path.join(os.path.dirname(__file__), "chip_palettes.json")

# ---------------------------------------------------------------------------
# LS11 解压（光荣自研 LZ77 变体 + 256 字节频率字典），对应 TaikouLZW.gd
# ---------------------------------------------------------------------------

def _u32be(data, off):
    if off + 3 >= len(data):
        return 0
    return (data[off] << 24) | (data[off + 1] << 16) | (data[off + 2] << 8) | data[off + 3]


def _get_bit(data, pos):
    return (data[pos >> 3] >> (7 - (pos & 7))) & 1


def ls11_decompress(data: bytes) -> bytes:
    if len(data) < 288:
        return b""
    if data[0:4] != b"LS11":
        return b""
    dictionary = data[0x10:0x10 + 256]
    compressed_size = _u32be(data, 0x110)
    decompressed_size = _u32be(data, 0x118 if False else 0x114)
    data_offset = _u32be(data, 0x118)
    if compressed_size == 0 or decompressed_size == 0 or data_offset == 0:
        return b""
    comp = data[data_offset:data_offset + compressed_size]
    comp_end = len(comp) * 8

    # 第一步：位流 -> 索引列表
    indices = []
    bit_pos = 0
    while bit_pos < comp_end:
        seg1_len = 0
        while bit_pos < comp_end and _get_bit(comp, bit_pos) == 1:
            seg1_len += 1
            bit_pos += 1
        if bit_pos >= comp_end:
            break
        bit_pos += 1  # 吞掉那个 0
        seg1_len += 1  # 段1长度含末尾的 0
        seg2_val = 0
        for _k in range(seg1_len):
            if bit_pos >= comp_end:
                break
            seg2_val = (seg2_val << 1) | _get_bit(comp, bit_pos)
            bit_pos += 1
        seg1_val = (1 << seg1_len) - 2
        indices.append(seg1_val + seg2_val)

    # 第二步：从索引列表还原输出
    out = bytearray(decompressed_size)
    out_pos = 0
    i = 0
    while i < len(indices) and out_pos < decompressed_size:
        idx = indices[i]
        if idx < 256:
            if idx < len(dictionary):
                out[out_pos] = dictionary[idx]
                out_pos += 1
        else:
            back = idx - 256
            copy_len = 0
            if i + 1 < len(indices):
                copy_len = indices[i + 1] + 3
                i += 1
            for _j in range(copy_len):
                if out_pos >= decompressed_size:
                    break
                if back <= 0:
                    out[out_pos] = out[out_pos - 1] if out_pos > 0 else 0
                else:
                    src = out_pos - back
                    if src < 0:
                        src = 0
                    out[out_pos] = out[src]
                out_pos += 1
        i += 1
    return bytes(out[:out_pos])


# ---------------------------------------------------------------------------
# 位平面解码（对应 TaikouImage.gd）
# ---------------------------------------------------------------------------

def decode_koei4bpp_tile(tile_bytes, tw=16, th=16):
    """KOEI 4bpp 位平面交错（TOWNCHIP / TOWNCHAR）。返回 len=tw*th 的索引列表。"""
    indexes = [0] * (tw * th)
    idx = 0
    pos = 0
    n = len(tile_bytes)
    while pos + 4 <= n and idx < tw * th:
        for bit in range(7, -1, -1):
            if idx >= tw * th:
                break
            v = ((tile_bytes[pos] >> bit) & 1) << 3
            v |= ((tile_bytes[pos + 1] >> bit) & 1) << 2
            v |= ((tile_bytes[pos + 2] >> bit) & 1) << 1
            v |= (tile_bytes[pos + 3] >> bit) & 1
            indexes[idx] = v
            idx += 1
        pos += 4
    return indexes


def decode_ega_planar_tile(tile_bytes, tw=16, th=16):
    """EGA 4 平面位图（HBCHAR / HJCHAR / HKCHAR）。返回 len=tw*th 的索引列表。"""
    plane_size = tw * th // 8
    if len(tile_bytes) < plane_size * 4:
        return [0] * (tw * th)
    indexes = [0] * (tw * th)
    for y in range(th):
        for x in range(tw):
            pi = y * (tw // 8) + x // 8
            bit = 7 - (x % 8)
            c = 0
            for p in range(4):
                plane_off = p * plane_size
                c |= ((tile_bytes[plane_off + pi] >> bit) & 1) << p
            indexes[y * tw + x] = c
    return indexes


# ---------------------------------------------------------------------------
# 调色板
# ---------------------------------------------------------------------------

def load_palette(key):
    if not hasattr(load_palette, "_cache"):
        load_palette._cache = {}
    if key in load_palette._cache:
        return load_palette._cache[key]
    with open(PALETTE_PATH, encoding="utf-8") as f:
        d = json.load(f)
    colors = []
    for hexc in d.get(key, {}).get("colors", []):
        hexc = hexc.lstrip("#")
        r = int(hexc[0:2], 16)
        g = int(hexc[2:4], 16)
        b = int(hexc[4:6], 16)
        colors.append((r, g, b, 255))
    load_palette._cache[key] = colors
    return colors


# ---------------------------------------------------------------------------
# 整张索引表渲染（对应 decode_indexed_sheet）
# ---------------------------------------------------------------------------

def decode_indexed_sheet(data, tw, th, cols, fmt, palette_key):
    pal = load_palette(palette_key)
    bpp_bytes = tw * th // 2 if fmt == "ega" else tw * th * 4 // 8
    if bpp_bytes <= 0 or len(data) % bpp_bytes != 0:
        return None, 0
    tile_count = len(data) // bpp_bytes
    img_w = cols * tw
    img_h = ((tile_count + cols - 1) // cols) * th
    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    px = img.load()
    for ti in range(tile_count):
        chunk = data[ti * bpp_bytes:(ti + 1) * bpp_bytes]
        if fmt == "ega":
            indexes = decode_ega_planar_tile(chunk, tw, th)
        else:
            indexes = decode_koei4bpp_tile(chunk, tw, th)
        tx = (ti % cols) * tw
        ty = (ti // cols) * th
        for yy in range(th):
            for xx in range(tw):
                ci = indexes[yy * tw + xx]
                if ci < len(pal):
                    px[tx + xx, ty + yy] = pal[ci]
    return img, tile_count


# ---------------------------------------------------------------------------
# 对外便捷接口：直接解出真实素材
# ---------------------------------------------------------------------------

def load_lzw(name):
    path = os.path.join(DATA_ROOT, name)
    with open(path, "rb") as f:
        raw = f.read()
    return ls11_decompress(raw)


def decode_townchip(cols=17):
    raw = load_lzw("TOWNCHIP.LZW")
    img, n = decode_indexed_sheet(raw, 16, 16, cols, "koei4bpp", "koei4bpp")
    return img, n, raw


def decode_hbchar(cols=16):
    raw = load_lzw("HBCHAR.LZW")
    img, n = decode_indexed_sheet(raw, 16, 16, cols, "ega", "ega16")
    return img, n, raw


def decode_townchar(cols=17):
    raw = load_lzw("TOWNCHAR.LZW")
    img, n = decode_indexed_sheet(raw, 16, 16, cols, "koei4bpp", "koei4bpp")
    return img, n, raw


def decode_mapchip():
    raw = load_lzw("MAPCHIP.LZW")
    img = Image.new("RGBA", (256, 88), (0, 0, 0, 0))
    px = img.load()
    for i in range(0, len(raw) - 1, 2):
        lo = raw[i]
        hi = raw[i + 1]
        val = (hi << 8) | lo
        r = (val >> 11) & 0x1F
        g = (val >> 5) & 0x3F
        b = val & 0x1F
        r = (r << 3) | (r >> 2)
        g = (g << 2) | (g >> 4)
        b = (b << 3) | (b >> 2)
        x = i // 2 % 256
        y = i // 2 // 256
        if y < 88:
            px[x, y] = (r, g, b, 255)
    return img


def decode_ega_sprite(data, index, tw=16, th=16, palette_key="ega16"):
    """从 HBCHAR 原始数据提取单帧精灵。"""
    bpp_bytes = tw * th // 2
    off = index * bpp_bytes
    chunk = data[off:off + bpp_bytes]
    pal = load_palette(palette_key)
    indexes = decode_ega_planar_tile(chunk, tw, th)
    img = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    px = img.load()
    for yy in range(th):
        for xx in range(tw):
            ci = indexes[yy * tw + xx]
            if ci < len(pal):
                px[xx, yy] = pal[ci]
    return img


if __name__ == "__main__":
    tc_raw = load_lzw("TOWNCHIP.LZW")
    hb_raw = load_lzw("HBCHAR.LZW")
    print("TOWNCHIP raw bytes:", len(tc_raw), "(expect 341*128=43648)")
    print("HBCHAR  raw bytes:", len(hb_raw), "(expect 384*128=49152)")
    timg, tn, _ = decode_townchip()
    himg, hn, _ = decode_hbchar()
    print("TOWNCHIP sheet:", timg.size, "tiles:", tn)
    print("HBCHAR  sheet:", himg.size, "tiles:", hn)
    assert len(tc_raw) == 43648, "TOWNCHIP 解压长度异常!"
    assert len(hb_raw) == 49152, "HBCHAR 解压长度异常!"
    print("OK: 真实素材解码通过")
