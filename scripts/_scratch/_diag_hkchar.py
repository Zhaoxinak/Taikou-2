"""Diagnostic: render HKCHAR glyph 0 in several bit-orderings as ASCII art,
and render system 啊 alongside, to determine the correct EGA decode + ordering."""
import os, sys
from PIL import Image, ImageFont, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from real_assets import ls11_decompress

DATA = "F:/Games/Taikou2"
dec = ls11_decompress(open(os.path.join(DATA, "HKCHAR.LZW"), "rb").read())
print(f"HKCHAR decompressed size = {len(dec)}, glyphs(32B) = {len(dec)//32}")

def glyph_mono_msb(chunk):
    bm = [0]*256
    for y in range(16):
        row = (chunk[y*2] << 8) | chunk[y*2+1]
        for x in range(16):
            if (row >> (15-x)) & 1:
                bm[y*16+x] = 1
    return bm

def glyph_mono_lsb(chunk):
    bm = [0]*256
    for y in range(16):
        row = (chunk[y*2] << 8) | chunk[y*2+1]
        for x in range(16):
            if (row >> x) & 1:
                bm[y*16+x] = 1
    return bm

def glyph_mono_byteswap(chunk):
    bm = [0]*256
    for y in range(16):
        b0, b1 = chunk[y*2], chunk[y*2+1]
        row = (b1 << 8) | b0
        for x in range(16):
            if (row >> (15-x)) & 1:
                bm[y*16+x] = 1
    return bm

def art(bm):
    return "\n".join("".join("#" if bm[y*16+x] else "." for x in range(16)) for y in range(16))

g0 = dec[0:32]
print("\n--- HKCHAR glyph 0, MSB-first ---\n" + art(glyph_mono_msb(g0)))
print("\n--- HKCHAR glyph 0, LSB-first ---\n" + art(glyph_mono_lsb(g0)))
print("\n--- HKCHAR glyph 0, byte-swapped MSB ---\n" + art(glyph_mono_byteswap(g0)))

# system 啊
font = ImageFont.truetype("C:/Windows/Fonts/simsun.ttc", 16)
img = Image.new("L", (16,16), 0)
ImageDraw.Draw(img).text((0,0), "啊", fill=255, font=font)
px = img.load()
sysbm = [1 if px[x,y] > 127 else 0 for y in range(16) for x in range(16)]
print("\n--- system 啊 ---\n" + art(sysbm))

# Also: how many bits set in glyph 0 under each decode?
for name, fn in [("msb", glyph_mono_msb), ("lsb", glyph_mono_lsb), ("bswap", glyph_mono_byteswap)]:
    print(f"glyph0 bits ({name}) = {sum(fn(g0))}")
print(f"system 啊 bits = {sum(sysbm)}")
