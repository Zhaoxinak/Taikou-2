#!/usr/bin/env python3
# Self-verify HJMAP/HKMAP tile structure via ASCII (we can read text, not PNG).
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from real_assets import ls11_decompress

ROOT = "F:/Games/Taikou2"
RAMPS = " .:-=+*#%@"  # 10-level brightness ramp (dark->light)

def ascii_tile(dec, ti, tw, th, bpp):
    bpp_bytes = tw*th if bpp==8 else tw*th//2
    off = ti*bpp_bytes
    lines=[]
    for y in range(th):
        row=""
        for x in range(tw):
            i=y*tw+x
            if bpp==8:
                v=dec[off+i]
            else:
                nb=dec[off+i//2]
                v=(nb>>(4 if i%2==0 else 0))&0xF
                v=v*255//15
            row+=RAMPS[min(9, v*9//255)]
        lines.append(row)
    return "\n".join(lines)

def info(name):
    raw=open(os.path.join(ROOT,name),"rb").read()
    dec=ls11_decompress(raw)
    print(f"\n########## {name}  (DEC={len(dec)}) ##########")
    if not dec: 
        print("  fail"); return
    # HJMAP: 180 x 256B (16x16 8bpp)
    if len(dec)%256==0:
        print(f"  -> divisible by 256 (16x16 8bpp): {len(dec)//256} tiles")
        for t in range(min(4, len(dec)//256)):
            print(f"  --- tile {t} (16x16 8bpp) ---")
            print(ascii_tile(dec,t,16,16,8))
    if len(dec)%128==0:
        print(f"  -> divisible by 128 (16x16 4bpp): {len(dec)//128} tiles")
    # bitmap candidates
    for w in (240,256,320,480):
        if len(dec)%w==0:
            h=len(dec)//w
            if h<=w*2:
                print(f"  -> bitmap {w}x{h} (8bpp)")

for f in ["HJMAP.LZW","HKMAP.LZW"]:
    info(f)
