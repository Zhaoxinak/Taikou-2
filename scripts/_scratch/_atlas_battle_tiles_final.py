#!/usr/bin/env python3
# Final battle-tile atlases for user visual confirmation (we can't see PNGs).
# HJMAP = 180 x 16x16 8bpp tiles (validated via ASCII).
# HKMAP = 52320B single 8bpp bitmap -> candidates 240x218 / 480x109.
import os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
from real_assets import ls11_decompress

ROOT = "F:/Games/Taikou2"
OUT = os.path.join(os.path.dirname(__file__), "_probe", "battle_tiles")
os.makedirs(OUT, exist_ok=True)

def save(name, dec, w, h, mode):
    if mode == "tiles16":
        tw=th=16; cols=20
        n=len(dec)//(tw*th)
        img=Image.new("L",(cols*tw, ((n+cols-1)//cols)*th),0)
        px=img.load()
        for ti in range(n):
            off=ti*tw*th; tx=(ti%cols)*tw; ty=(ti//cols)*th
            for i in range(tw*th):
                px[tx+(i%tw), ty+(i//tw)]=dec[off+i]
    elif mode=="bitmap":
        img=Image.new("L",(w,h),0); px=img.load()
        for i in range(w*h):
            if i<len(dec): px[i%w, i//w]=dec[i]
    path=os.path.join(OUT,name)
    img.save(path)
    print("saved",path,img.size)

hj=ls11_decompress(open(os.path.join(ROOT,"HJMAP.LZW"),"rb").read())
hk=ls11_decompress(open(os.path.join(ROOT,"HKMAP.LZW"),"rb").read())

print("HJMAP tiles (180 x 16x16 8bpp):")
save("HJMAP_16x16_8bpp_tiles.png", hj, 0,0,"tiles16")
print("HKMAP bitmap candidates (8bpp):")
save("HKMAP_240x218.png", hk, 240,218,"bitmap")
save("HKMAP_480x109.png", hk, 480,109,"bitmap")
# also HKMAP as 16x15 tiles (218) in case it's a tile set
save("HKMAP_16x15_tiles.png", hk, 0,0,"tiles16")  # will mis-divide but try
print("done")
