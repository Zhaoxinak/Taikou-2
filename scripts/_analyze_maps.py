#!/usr/bin/env python3
import os
from math import log2
SRC = "F:/Games/Taikou2"

def ls11_decompress(data):
    if len(data) < 288 or data[:4] != b'LS11':
        return None
    dictionary = list(data[0x10:0x10+256])
    compressed_size = int.from_bytes(data[0x110:0x114], 'big')
    decompressed_size = int.from_bytes(data[0x114:0x118], 'big')
    data_offset = int.from_bytes(data[0x118:0x11C], 'big')   # FIX: 4 bytes not 8
    if not (compressed_size and decompressed_size and data_offset):
        return None
    comp = data[data_offset:data_offset+compressed_size]
    comp_end = len(comp)*8
    indices = []
    bit_pos = 0
    while bit_pos < comp_end:
        seg1_len = 0
        while bit_pos < comp_end and (comp[bit_pos>>3] >> (7-(bit_pos&7))) & 1 == 1:
            seg1_len += 1; bit_pos += 1
        if bit_pos >= comp_end: break
        bit_pos += 1
        seg1_len += 1
        seg2_val = 0
        for _k in range(seg1_len):
            if bit_pos >= comp_end: break
            seg2_val = (seg2_val << 1) | ((comp[bit_pos>>3] >> (7-(bit_pos&7))) & 1)
            bit_pos += 1
        seg1_val = (1 << seg1_len) - 2
        indices.append(seg1_val + seg2_val)
    out = bytearray(decompressed_size)
    out_pos = 0; i = 0
    while i < len(indices) and out_pos < decompressed_size:
        idx = indices[i]
        if idx < 256:
            if idx < len(dictionary):
                out[out_pos] = dictionary[idx]; out_pos += 1
        else:
            back = idx - 256
            copy_len = 0
            if i+1 < len(indices):
                copy_len = indices[i+1] + 3; i += 1
            for _j in range(copy_len):
                if out_pos >= decompressed_size: break
                if back <= 0:
                    out[out_pos] = out[out_pos-1] if out_pos>0 else 0
                else:
                    src = out_pos - back
                    if src < 0: src = 0
                    out[out_pos] = out[src]
                out_pos += 1
        i += 1
    return bytes(out[:out_pos])

def entropy(b):
    cnt=[0]*256
    for x in b: cnt[x]+=1
    n=len(b); e=0.0
    for c in cnt:
        if c: p=c/n; e-=p*log2(p)
    return e

def coh8(buf,w,h):
    if w*h>len(buf): return None
    s=c=0
    for y in range(h):
        for x in range(w):
            v=buf[y*w+x]
            if x+1<w: s+=abs(v-buf[y*w+x+1]); c+=1
            if y+1<h: s+=abs(v-buf[(y+1)*w+x]); c+=1
    return s/c

def coh565(buf,w,h):
    if w*h*2>len(buf): return None
    def px(x,y):
        o=(y*w+x)*2; v=buf[o]|(buf[o+1]<<8); return ((v>>11)&0x1f,(v>>5)&0x3f,v&0x1f)
    s=c=0
    for y in range(h):
        for x in range(w):
            r,g,b=px(x,y)
            if x+1<w:
                r2,g2,b2=px(x+1,y); s+=abs(r-r2)+abs(g-g2)+abs(b-b2); c+=1
            if y+1<h:
                r2,g2,b2=px(x,y+1); s+=abs(r-r2)+abs(g-g2)+abs(b-b2); c+=1
    return s/c

def analyze(name, buf):
    print(f"\n=== {name} === decompressed {len(buf)} B, entropy(byte)={entropy(buf):.3f}")
    # candidate (header, w, h, fmt)
    cands=[]
    for hdr in (0,6):
        b=buf[hdr:]
        n=len(b)
        for (w,h) in [(256,88),(256,176),(512,88),(352,128),(176,256),(320,180),
                      (192,120),(240,96),(192,240),(320,144),(256,180),(480,109),
                      (256,204),(320,163),(288,160),(360,128),(240,144),(160,288),
                      (256,90),(192,136),(256,102),(256,144),(176,144),(256,120),
                      (448,176),(128,352),(256,200),(512,44),(352,64)]:
            if w*h*2==n:
                c=coh565(b,w,h)
                if c is not None: cands.append((c,f"RGB565 hdr{hdr} {w}x{h}"))
            if w*h==n:
                c=coh8(b,w,h)
                if c is not None: cands.append((c,f"8bpp   hdr{hdr} {w}x{h}"))
    cands.sort()
    for c,desc in cands[:8]:
        print(f"   coh={c:6.2f}  {desc}")

files=["MAPCHIP.LZW","TOWNMAP.LZW","MAPCHAR.LZW","HBMAP.LZW","HJMAP.LZW","HKMAP.LZW","SHOPMAP.LZW"]
for f in files:
    p=os.path.join(SRC,f)
    if not os.path.exists(p):
        print(f"\n=== {f} === MISSING"); continue
    buf=ls11_decompress(open(p,'rb').read())
    if buf is None or len(buf)==0:
        print(f"\n=== {f} === decompress FAILED"); continue
    analyze(f,buf)
