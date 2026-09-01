
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>
import os, struct, sys
from PIL import Image
D=_ROOT + '/Taikou2 Original'
OUT=_ROOT + '/scripts/_decoded_grp'
os.makedirs(OUT, exist_ok=True)
def rd(n): return open(os.path.join(D,n),'rb').read()

# ---- 4bpp 解包两种假设 ----
def unpack_npkstyle(data, npix):
    """2 字节 -> 4 像素，NPK 字面量位序：b1.7->bit3, b1.3->bit2, b2.7->bit1, b2.3->bit0"""
    out=bytearray()
    i=0
    while i+1 < len(data) and len(out) < npix:
        b1=data[i]; b2=data[i+1]; i+=2
        for _ in range(4):
            d = ((b1&0x80)>>4) | ((b1&0x08)>>1) | ((b2&0x80)>>6) | ((b2&0x08)>>3)
            out.append(d & 0x0f)
            b1=(b1<<1)&0xff; b2=(b2<<1)&0xff
            if len(out)>=npix: break
    return out
def unpack_packed(data, npix):
    """标准 packed 4bpp：高半字节=左像素"""
    out=bytearray()
    for by in data:
        out.append(by>>4); out.append(by&0xf)
        if len(out)>=npix: break
    return out[:npix]

def pal_from_exe(va, mem, base=0x400000):
    o=va-base; p=[]
    for k in range(16):
        r,g,b = mem[o+3*k], mem[o+3*k+1], mem[o+3*k+2]
        p += [r*17, g*17, b*17]
    return p

MEM=open(_ROOT + '/scripts/_unpacked_mem.bin',"rb").read()

def save(idx, W,H, pal, name):
    im=Image.new("P",(W,H)); im.putdata(bytes(idx)); im.putpalette(pal+[0]*(768-len(pal)))
    im.convert("RGB").save(os.path.join(OUT,name))
    return name

# === 1. 三个 6 字节头 GRP ===
GREY=[i*17 for k in range(16) for i in (k,k,k)]
for fn, palva in (("ACERTWP.GRP",0x50a188),("KOEILOGO.GRP",0x50a2c0),("PRESS.GRP",None)):
    b=rd(fn); t,W,H=struct.unpack("<BxHH", b[:6]); body=b[6:]
    assert len(body)==W*H//2, (fn,len(body),W*H//2)
    pal = pal_from_exe(palva,MEM) if palva else GREY
    save(unpack_npkstyle(body, W*H), W,H, pal, fn.replace(".GRP","_npkstyle.png"))
    save(unpack_packed(body, W*H), W,H, pal, fn.replace(".GRP","_packed.png"))
    print(fn,"type=%d %dx%d body=%d"%(t,W,H,len(body)),"-> 2 PNG")

# === 2. NPK016 RLE 解码器（NPK_SPEC §3.1）===
def npk_rle(src, W, npix):
    out=bytearray(); bitflag=0; i=0
    while i < len(src) and len(out) < npix:
        if (bitflag & 0xff00)==0:
            if i>=len(src): break
            bitflag = 0xff00 | src[i]; i+=1
        if bitflag & 1:
            if i>=len(src): break
            bb=src[i]; i+=1
            run_size=(bb&0x1f)+1
            run_off=((bb&0x60)>>5)+1
            run_off = run_off*W if (bb&0x80) else run_off*4
            for _ in range(run_size*4):
                if len(out)>=npix: break
                s=len(out)-run_off
                out.append(out[s] if s>=0 else 0)
        else:
            if i+1>=len(src): break
            b1=src[i]; b2=src[i+1]; i+=2
            for _ in range(4):
                if len(out)>=npix: break
                d = ((b1&0x80)>>4)|((b1&0x08)>>1)|((b2&0x80)>>6)|((b2&0x08)>>3)
                out.append(d&0x0f); b1=(b1<<1)&0xff; b2=(b2<<1)&0xff
        bitflag >>= 1
    return out, i

# === 3. END.GRP 容器 ===
b=rd("END.GRP")
n0=struct.unpack(">I",b[:4])[0]; nent=n0//4
offs=[struct.unpack(">I",b[4*i:4*i+4])[0] for i in range(nent)]
print("\nEND.GRP: BE 偏移表 %d 项, 表长 %d, 文件 %d"%(nent,n0,len(b)))
magic_ok=sum(1 for o in offs if b[o:o+6]==b"NPK016")
print("  NPK016 magic 命中:", magic_ok, "/", nent, " 末项内容:", b[offs[-1]:offs[-1]+8])
hdrs=[]
for k,o in enumerate(offs):
    if b[o:o+6]!=b"NPK016": continue
    t=b[o+6]; dW,dH,nW,nH=struct.unpack("<4H", b[o+8:o+0x10])
    hdrs.append((k,o,t,dW,dH,nW,nH))
import collections
print("  头统计 type:",collections.Counter(h[2] for h in hdrs))
print("  display:",collections.Counter((h[3],h[4]) for h in hdrs))
print("  native :",collections.Counter((h[5],h[6]) for h in hdrs).most_common(8))
# 解码前若干条
ok=0; fails=[]
for (k,o,t,dW,dH,nW,nH) in hdrs:
    end = offs[k+1] if k+1<len(offs) else len(b)-3
    pal=[]
    for j in range(16):
        v=struct.unpack("<H", b[o+0x10+2*j:o+0x12+2*j])[0]
        pal += [((v>>8)&0xf)*17, ((v>>4)&0xf)*17, (v&0xf)*17]
    px,used = npk_rle(b[o+0x30:end], nW, nW*nH)
    if len(px)==nW*nH: ok+=1
    else: fails.append((k,len(px),nW*nH))
    if k<4 or k in (50,80,103):
        save(px+bytearray(nW*nH-len(px)), nW,nH, pal, "END_%03d_%dx%d.png"%(k,nW,nH))
print("  RLE 恰好填满: %d/%d"%(ok,len(hdrs)), "失败:",fails[:5])
