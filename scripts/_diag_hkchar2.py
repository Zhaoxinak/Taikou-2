"""Try multiple decode formats for HKCHAR/HJCHAR glyph 0 and view as ASCII art."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from real_assets import ls11_decompress

DATA = "F:/Games/Taikou2"

def decode(name):
    return ls11_decompress(open(os.path.join(DATA, name), "rb").read())

def art(bm, w=16, h=16):
    return "\n".join("".join("#" if bm[y*w+x] else "." for x in range(w)) for y in range(h))

def g_1plane(chunk, w=16, h=16):
    bm=[0]*(w*h)
    for y in range(h):
        row=(chunk[y*2]<<8)|chunk[y*2+1]
        for x in range(w):
            bm[y*w+x]=1 if (row>>(w-1-x))&1 else 0
    return bm

def g_2plane_or(chunk, w=16, h=16):
    # like HBCHAR2: 2 planes of 32B, OR combine
    bm=[0]*(w*h)
    for y in range(h):
        r0=(chunk[y*2]<<8)|chunk[y*2+1]
        r1=(chunk[32+y*2]<<8)|chunk[32+y*2+1]
        row=r0|r1
        for x in range(w):
            bm[y*w+x]=1 if (row>>(w-1-x))&1 else 0
    return bm

def g_2plane_p0(chunk, w=16, h=16):
    return g_1plane(chunk[:32], w, h)
def g_2plane_p1(chunk, w=16, h=16):
    return g_1plane(chunk[32:64], w, h)

for name in ["HKCHAR.LZW", "HJCHAR.LZW"]:
    dec = decode(name)
    print(f"\n########## {name}  size={len(dec)}  (32B->{len(dec)//32} | 64B->{len(dec)//64}) ##########")
    for gi in [0, 1, 2]:
        base = gi*64
        if base+64 <= len(dec):
            ch = dec[base:base+64]
            print(f"\n--- {name} glyph {gi} as 2-plane-64B (OR) ---\n" + art(g_2plane_or(ch)))
            print(f"--- {name} glyph {gi} plane0 only ---\n" + art(g_2plane_p0(ch)))
