"""Definitive pixel-level match test for font files.

For each font file, render glyph 0 with the assumed decode, render the *claimed*
character from a system CJK font, and report the pixel match score.
Also test several ALTERNATIVE decode formats in case the assumed one is wrong.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from real_assets import ls11_decompress
from PIL import Image, ImageFont, ImageDraw

DATA = "F:/Games/Taikou2"
FONTS = ["C:/Windows/Fonts/simsun.ttc", "C:/Windows/Fonts/msyh.ttc"]

font_cache = {}
def sys_glyph(ch, fontpath):
    if (ch, fontpath) in font_cache:
        return font_cache[(ch, fontpath)]
    font = ImageFont.truetype(fontpath, 16)
    img = Image.new("L", (16,16), 0)
    ImageDraw.Draw(img).text((0,-1), ch, fill=255, font=font)
    px = img.load()
    bm = [1 if px[x,y] > 127 else 0 for y in range(16) for x in range(16)]
    font_cache[(ch, fontpath)] = bm
    return bm

def decode_variants(chunk32):
    """Given first 32 bytes, produce multiple 256-bit interpretations."""
    out = {}
    # V1: 1-plane row-major MSB
    bm=[0]*256
    for y in range(16):
        row=(chunk32[y*2]<<8)|chunk32[y*2+1]
        for x in range(16):
            bm[y*16+x]=1 if (row>>(15-x))&1 else 0
    out["1plane_msb"]=bm
    # V2: 1-plane row-major LSB
    bm=[0]*256
    for y in range(16):
        row=(chunk32[y*2]<<8)|chunk32[y*2+1]
        for x in range(16):
            bm[y*16+x]=1 if (row>>x)&1 else 0
    out["1plane_lsb"]=bm
    # V3: column-major (16 cols, 2 bytes each, MSB=row0)
    bm=[0]*256
    for x in range(16):
        row=(chunk32[x*2]<<8)|chunk32[x*2+1]
        for y in range(16):
            bm[y*16+x]=1 if (row>>(15-y))&1 else 0
    out["col_major"]=bm
    return out

def decode_2plane_or(chunk64):
    bm=[0]*256
    for y in range(16):
        r0=(chunk64[y*2]<<8)|chunk64[y*2+1]
        r1=(chunk64[32+y*2]<<8)|chunk64[32+y*2+1]
        row=r0|r1
        for x in range(16):
            bm[y*16+x]=1 if (row>>(15-x))&1 else 0
    return bm

def decode_4plane_or(chunk128):
    bm=[0]*256
    for y in range(16):
        row=0
        for p in range(4):
            row |= (chunk128[p*32+y*2]<<8)|chunk128[p*32+y*2+1]
        for x in range(16):
            bm[y*16+x]=1 if (row>>(15-x))&1 else 0
    return bm

def match(a, b):
    if sum(a)==0 and sum(b)==0: return 1.0
    inter=sum(1 for i in range(256) if a[i] and b[i])
    union=sum(1 for i in range(256) if a[i] or b[i])
    return inter/union if union else 0

def test_file(fname, gsize, claim_char, claim_name):
    raw=open(os.path.join(DATA,fname),"rb").read()
    dec=ls11_decompress(raw)
    if not dec: print(f"{fname}: decompress fail"); return
    n=len(dec)//gsize
    chunk=dec[:gsize]
    print(f"\n========== {fname}  dec={len(dec)}  n={n}  claim=glyph0='{claim_char}' ==========")
    # render system char under both fonts
    for fp in FONTS:
        ref=sys_glyph(claim_char, fp)
        print(f"  system '{claim_char}' via {os.path.basename(fp)}: bits={sum(ref)}")
    # try all decodes
    for vname, bm in decode_variants(chunk[:32]).items():
        for fp in FONTS:
            ref=sys_glyph(claim_char, fp)
            s=match(bm,ref)
            print(f"  decode={vname:14s}  bits={sum(bm):3d}  vs {os.path.basename(fp):12s}  match={s:.3f}")
    if gsize>=64:
        bm=decode_2plane_or(chunk[:64])
        for fp in FONTS:
            ref=sys_glyph(claim_char, fp)
            print(f"  decode=2plane_or       bits={sum(bm):3d}  vs {os.path.basename(fp):12s}  match={match(bm,ref):.3f}")
    if gsize>=128:
        bm=decode_4plane_or(chunk[:128])
        for fp in FONTS:
            ref=sys_glyph(claim_char, fp)
            print(f"  decode=4plane_or       bits={sum(bm):3d}  vs {os.path.basename(fp):12s}  match={match(bm,ref):.3f}")

# HKCHAR claimed start=啊 (0xB0A1), 32B
test_file("HKCHAR.LZW", 32, "啊", "GBK 0xB0A1")
# HJCHAR
test_file("HJCHAR.LZW", 32, "啊", "test 啊 first")
# TOWNCHAR
test_file("TOWNCHAR.LZW", 32, "啊", "test 啊 first")
# MAPCHAR
test_file("MAPCHAR.LZW", 32, "啊", "test 啊 first")
# HBCHAR2: prior claim glyph0=北 (name table)
test_file("HBCHAR2.LZW", 64, "北", "name table glyph 0")
# Also test HBCHAR2 with 啊 (just in case it's actually GBK-ordered)
raw=open(os.path.join(DATA,"HBCHAR2.LZW"),"rb").read()
dec=ls11_decompress(raw)
chunk=dec[:64]
for vname,bm in decode_variants(chunk[:32]).items():
    for fp in FONTS:
        ref=sys_glyph("啊",fp)
        print(f"  HBCHAR2 decode={vname:14s}  vs 啊 {os.path.basename(fp):12s}  match={match(bm,ref):.3f}")
bm=decode_2plane_or(chunk)
for fp in FONTS:
    ref=sys_glyph("啊",fp)
    print(f"  HBCHAR2 decode=2plane_or       vs 啊 {os.path.basename(fp):12s}  match={match(bm,ref):.3f}")
