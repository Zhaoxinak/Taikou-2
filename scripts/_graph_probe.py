#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图形格式逆向探测工具 (太阁立志传2 / Taikou Risshiden 2)
=======================================================
把 LS11 压缩的图形文件按多种 (bpp, tile尺寸, 排列) 假设渲染成灰度 PNG，
肉眼(Read 工具)判断哪一种解释能还原出真实的地图块/精灵，从而锁定像素格式。

用法:
  python _graph_probe.py <FILE> --bpp 8|4|1 --tile 16x16 --cols 16 --out out.png
  python _graph_probe.py <FILE> --bpp 8 --tile 24x24 --cols 10 --out out.png

说明:
  - FILE 可以是 .LZW (自动 LS11 解压) 或直接像素文件
  - 灰度模式下 8bpp 直接用字节值; 4bpp 每个 nibble *17; 1bpp 每个 bit *255
  - 若后续找到调色板, 可加 --pal pal.bin (256*3 RGB) 渲染真彩
"""
import sys, os, struct, zlib, argparse


def u32be(d, o):
    return (d[o] << 24) | (d[o + 1] << 16) | (d[o + 2] << 8) | d[o + 3]


def gb(d, p):
    return (d[p >> 3] >> (7 - (p & 7))) & 1


def ls11(data):
    """已 100% 验证的 LS11 解压器 (Koei LZ77 变体 + 256B 字典)."""
    dic = data[0x10:0x10 + 256]
    cs = u32be(data, 0x110)
    ds = u32be(data, 0x114)
    off = u32be(data, 0x118)
    comp = data[off:off + cs]
    ce = len(comp) * 8
    idx = []
    bp = 0
    while bp < ce:
        s1 = 0
        while bp < ce and gb(comp, bp) == 1:
            s1 += 1
            bp += 1
        if bp >= ce:
            break
        bp += 1
        s1 += 1
        s2 = 0
        for _ in range(s1):
            if bp >= ce:
                break
            s2 = (s2 << 1) | gb(comp, bp)
            bp += 1
        idx.append((1 << s1) - 2 + s2)
    out = bytearray()
    op = 0
    i = 0
    while i < len(idx) and op < ds:
        v = idx[i]
        if v < 256:
            if v < len(dic):
                out.append(dic[v])
            op += 1
        else:
            back = v - 256
            cl = 0
            if i + 1 < len(idx):
                cl = idx[i + 1] + 3
                i += 1
            for _ in range(cl):
                if op >= ds:
                    break
                src = op - back
                if src < 0:
                    src = 0
                out.append(out[src] if src < len(out) else 0)
                op += 1
        i += 1
    return bytes(out[:op])


def write_png_gray(path, w, h, buf):
    def chunk(typ, data):
        c = typ + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)

    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)  # 8-bit grayscale
    raw = b''
    for y in range(h):
        raw += b'\x00' + buf[y * w:(y + 1) * w]
    idat = zlib.compress(raw, 9)
    png = sig + chunk(b'IHDR', ihdr) + chunk(b'IDAT', idat) + chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(png)


def write_png_rgb(path, w, h, rgb_buf):
    """Write a 24-bit RGB PNG. rgb_buf must be exactly w*h*3 bytes."""
    def chunk(typ, data):
        c = typ + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8-bit RGB
    raw = b''
    for y in range(h):
        raw += b'\x00' + rgb_buf[y * w * 3:(y + 1) * w * 3]
    idat = zlib.compress(raw, 9)
    png = sig + chunk(b'IHDR', ihdr) + chunk(b'IDAT', idat) + chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(png)


def decode_rgb565(buf):
    """Decode RGB565 (LE) pixel buffer to RGB24 bytearray."""
    out = bytearray(len(buf) // 2 * 3)
    for i in range(len(buf) // 2):
        p = struct.unpack('<H', buf[i * 2:i * 2 + 2])[0]
        r = ((p >> 11) & 0x1f) * 255 // 31
        g = ((p >> 5) & 0x3f) * 255 // 63
        b = (p & 0x1f) * 255 // 31
        out[i * 3] = r & 0xff
        out[i * 3 + 1] = g & 0xff
        out[i * 3 + 2] = b & 0xff
    return bytes(out)


def render_grp(data, out):
    """
    KOEI GRP format: 6-byte header + RGB565 pixel data.
    Header: [04 00][XX XX][YY YY] where XX*YY encodes 2x actual resolution.
    Verified files: ACERTWP.GRP, PRESS.GRP, KOEILOGO.GRP (all 320x200).
    """
    if len(data) < 6:
        print("  ERROR: file too short for GRP format")
        return
    hdr = data[:6]
    px = data[6:]
    # Try to infer resolution from pixel area (must be w*h*2 == len(px))
    found = False
    for w, h in [(320, 200), (640, 400), (640, 480), (800, 600), (320, 240)]:
        if len(px) == w * h * 2:
            rgb = decode_rgb565(px)
            write_png_rgb(out, w, h, rgb)
            print(f"  GRP -> {out} ({w}x{h} RGB565) head={hdr.hex()}")
            found = True
            break
    if not found:
        # Fallback: try header-encoded dimensions
        # Some GRP headers store 2x actual size
        for divisor in [2, 1]:
            hw = struct.unpack('<H', hdr[2:4])[0] // divisor
            hh = struct.unpack('<H', hdr[4:6])[0] // divisor
            if hw > 0 and hh > 0 and len(px) == hw * hh * 2:
                rgb = decode_rgb565(px)
                write_png_rgb(out, hw, hh, rgb)
                print(f"  GRP -> {out} ({hw}x{hh} RGB565) head={hdr.hex()} (header/{divisor})")
                found = True
                break
    if not found:
        print(f"  GRP: could not determine resolution (pixel_area={len(px)}, head={hdr.hex()})")


def render_koei4bpp_sheet(d, tw, th, cols, pal_rgb, out):
    """KOEI 4bpp bit-plane interleaved tiles (TOWNCHIP)."""
    part = tw * th * 4 // 8
    n = len(d) // part
    rows = (n + cols - 1) // cols
    W, H = cols * tw, rows * th
    buf = bytearray(W * H * 3)
    for ti in range(n):
        idx = to_4bpp_indexes(d[ti * part:(ti + 1) * part])
        tx, ty = (ti % cols) * tw, (ti // cols) * th
        for yy in range(th):
            for xx in range(tw):
                pi = yy * tw + xx
                if pi < len(idx):
                    c = pal_rgb[idx[pi] % len(pal_rgb)]
                    di = ((ty + yy) * W + (tx + xx)) * 3
                    buf[di:di + 3] = c
    write_png_rgb(out, W, H, bytes(buf))
    print(f"  KOEI4bpp -> {out} ({W}x{H}, {n} tiles)")


def to_4bpp_indexes(data):
    indexes = []
    for g in grouper(data, 4):
        if len(g) < 4:
            break
        for i in range(7, -1, -1):
            indexes.append(
                (((g[0] >> i) & 1) << 3) | (((g[1] >> i) & 1) << 2) |
                (((g[2] >> i) & 1) << 1) | ((g[3] >> i) & 1)
            )
    return indexes


def grouper(data, n):
    return [data[i:i + n] for i in range(0, len(data), n)]


def ega_planar_indexes(chunk, w, h):
    plane_size = w * h // 8
    planes = [chunk[i * plane_size:(i + 1) * plane_size] for i in range(4)]
    idx = []
    for y in range(h):
        for x in range(w):
            pi = y * (w // 8) + x // 8
            bit = 7 - (x % 8)
            c = sum(((planes[p][pi] >> bit) & 1) << p for p in range(4))
            idx.append(c)
    return idx


def render_ega_sheet(d, tw, th, cols, pal_rgb, out):
    """EGA 4-plane planar tiles (HBCHAR / HJCHAR / HKCHAR)."""
    part = tw * th // 2
    n = len(d) // part
    rows = (n + cols - 1) // cols
    W, H = cols * tw, rows * th
    buf = bytearray(W * H * 3)
    for ti in range(n):
        idx = ega_planar_indexes(d[ti * part:(ti + 1) * part], tw, th)
        tx, ty = (ti % cols) * tw, (ti // cols) * th
        for yy in range(th):
            for xx in range(tw):
                c = pal_rgb[idx[yy * tw + xx] % len(pal_rgb)]
                di = ((ty + yy) * W + (tx + xx)) * 3
                buf[di:di + 3] = c
    write_png_rgb(out, W, H, bytes(buf))
    print(f"  EGA -> {out} ({W}x{H}, {n} sprites)")


DOS16_PAL = [
    (0, 0, 0), (85, 255, 85), (255, 85, 85), (255, 255, 85),
    (85, 85, 255), (85, 255, 255), (255, 85, 255), (255, 255, 255),
    (0, 0, 0), (0, 170, 0), (170, 0, 0), (170, 170, 0),
    (0, 0, 170), (0, 170, 170), (170, 0, 170), (170, 170, 170),
]

EGA16_PAL = [
    (0, 0, 0), (0, 0, 170), (0, 170, 0), (0, 170, 170),
    (170, 0, 0), (170, 0, 170), (170, 85, 0), (170, 170, 170),
    (85, 85, 85), (85, 85, 255), (85, 255, 85), (85, 255, 255),
    (255, 85, 85), (255, 85, 255), (255, 255, 85), (255, 255, 255),
]


def render(d, bpp, tw, th, cols, out, pal=None):
    if bpp == 8:
        npix = len(d)
    elif bpp == 4:
        npix = len(d) * 2
    else:  # 1
        npix = len(d) * 8
    ntiles = npix // (tw * th)
    rows = (ntiles + cols - 1) // cols
    W = cols * tw
    H = rows * th
    buf = bytearray(W * H)

    def val(i):
        if bpp == 8:
            return d[i]
        if bpp == 4:
            byte = d[i >> 1]
            return (byte >> 4) & 0xf if (i & 1) == 0 else byte & 0xf
        # 1bpp
        byte = d[i >> 3]
        return (byte >> (7 - (i & 7))) & 1

    for ti in range(ntiles):
        tx = (ti % cols) * tw
        ty = (ti // cols) * th
        for yy in range(th):
            for xx in range(tw):
                i = ti * tw * th + yy * tw + xx
                v = val(i)
                if pal:
                    v = pal[v]
                else:
                    v = v * 17 if bpp == 4 else (v * 255 if bpp == 1 else v)
                buf[(ty + yy) * W + (tx + xx)] = v & 0xff
    write_png_gray(out, W, H, bytes(buf))
    return ntiles, W, H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--mode", default="tile", choices=["tile", "grp", "mapchip", "townchip", "ega"],
                    help="tile=indexed+tile; grp=RGB565 GRP; mapchip=RGB565 chip; townchip=KOEI4bpp; ega=EGA planar")
    ap.add_argument("--bpp", type=int, default=8)
    ap.add_argument("--tile", default="16x16")
    ap.add_argument("--cols", type=int, default=16)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pal", default=None, help="optional 256*3 RGB palette file for truecolor")
    args = ap.parse_args()

    raw = open(args.file, 'rb').read()
    d = ls11(raw) if raw[:4] == b'LS11' else raw

    if args.mode == "grp":
        render_grp(d, args.out)
        return

    if args.mode == "mapchip":
        # MAPCHIP = bare RGB565, 256×88
        rgb = decode_rgb565(d)
        write_png_rgb(args.out, 256, 88, rgb)
        print(f"  MAPCHIP -> {args.out} (256x88 RGB565)")
        return

    if args.mode == "townchip":
        tw, th = 16, 16
        render_koei4bpp_sheet(d, tw, th, args.cols, DOS16_PAL, args.out)
        return

    if args.mode == "ega":
        tw, th = 16, 16
        render_ega_sheet(d, tw, th, args.cols, EGA16_PAL, args.out)
        return

    tw, th = map(int, args.tile.split('x'))
    pal = None
    if args.pal:
        pb = open(args.pal, 'rb').read()
        pal = list(pb)  # flat 0-255
        # Ensure all palette values are in 0-255
        pal = [min(max(v, 0), 255) for v in pal]
    n, W, H = render(d, args.bpp, tw, th, args.cols, args.out, pal)
    print(f"OK {os.path.basename(args.file)} bpp={args.bpp} tile={tw}x{th} tiles={n} -> {args.out} ({W}x{H})")


if __name__ == "__main__":
    main()
