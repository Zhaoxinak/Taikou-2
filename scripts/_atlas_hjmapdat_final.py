import struct, collections
from PIL import Image, ImageDraw, ImageFont

buf = open('F:/Games/Taikou2/HJMAPDAT.DAT','rb').read()
REC = 1700
N = len(buf)//REC  # 38

# ---- categorical palette for terrain (low nibble 0-15) and A (0-7) ----
TERR_COL = {
 0:(120,160,200), 1:(90,200,120), 2:(200,210,120), 3:(170,200,150),
 4:(150,120,90), 5:(200,160,120), 6:(60,140,70), 7:(100,170,100),
 8:(160,120,90), 9:(180,180,180), 10:(190,160,140), 11:(140,110,80),
 12:(120,120,140), 13:(110,110,120), 14:(150,150,160), 15:(200,200,210)}
A_COL = {i:tuple(int(255*c/7) for c in ((i*37)%256,(i*91)%256,(i*53+80)%256)) for i in range(8)}

# ---- A-zones atlas (20x9) for all 38 records ----
tw, th = 20, 9
scale = 12
AW = tw*scale; AH = th*scale
cols = 6
rows = (N+cols-1)//cols
imgA = Image.new('RGB',(cols*AW+ (cols+1)*4, rows*AH+(rows+1)*4),(30,30,30))
dA = ImageDraw.Draw(imgA)
for r in range(N):
    rec = buf[r*REC:r*REC+REC]
    A = rec[0:180]
    gx = (r%cols); gy = (r//cols)
    ox = 4+gx*(AW+4); oy = 4+gy*(AH+4)
    for y in range(th):
        for x in range(tw):
            v = A[y*20+x]
            dA.rectangle([ox+x*scale,oy+y*scale,ox+x*scale+scale-1,oy+y*scale+scale-1],
                         fill=A_COL.get(v,(0,0,0)))
    dA.text((ox+2,oy+2), f"r{r}", fill=(255,255,0))
imgA.save('_probe/battle_maps/hjmapdat_A_zones_20x9.png')
print('saved A-zones atlas', imgA.size)

# ---- Record 0 explained: terrain + ASCII-C + A-zones ----
rec = buf[0:REC]
B = rec[180:940]; C = rec[940:1700]; A = rec[0:180]
CW, CH = 40, 19
cs = 14
def panel_terrain():
    im = Image.new('RGB',(CW*cs,CH*cs),(0,0,0)); d=ImageDraw.Draw(im)
    for y in range(CH):
        for x in range(CW):
            v = B[y*40+x]; terr = v & 0xF
            d.rectangle([x*cs,y*cs,x*cs+cs-1,y*cs+cs-1], fill=TERR_COL.get(terr,(0,0,0)))
    return im
def panel_ascii():
    im = Image.new('RGB',(CW*cs,CH*cs),(20,20,20)); d=ImageDraw.Draw(im)
    try: f = ImageFont.load_default()
    except: f = None
    for y in range(CH):
        for x in range(CW):
            v = C[y*40+x]
            ch = '.' if v==255 else (chr(v) if 32<=v<127 else '?')
            if ch!='.':
                d.text((x*cs+2,y*cs+1), ch, fill=(230,230,120), font=f)
    return im
def panel_a():
    im = Image.new('RGB',(20*cs,9*cs),(0,0,0)); d=ImageDraw.Draw(im)
    for y in range(9):
        for x in range(20):
            v=A[y*20+x]
            d.rectangle([x*cs,y*cs,x*cs+cs-1,y*cs+cs-1], fill=A_COL.get(v,(0,0,0)))
    return im
t=panel_terrain(); a=panel_ascii(); z=panel_a()
W = t.width+a.width+40; H = max(t.height,z.height)+30
im = Image.new('RGB',(W,H+40),(40,40,40)); d=ImageDraw.Draw(im)
im.paste(t,(0,30)); d.text((0,8),'B terrain 40x19 (low nibble=type)',fill=(255,255,255))
im.paste(a,(t.width+20,30)); d.text((t.width+20,8),'C deployment 40x19 (ASCII)',fill=(255,255,255))
im.paste(z,(0,t.height+35)); d.text((0,t.height+18),'A zones 20x9 (cat 0-7)',fill=(255,255,255))
im.save('_probe/battle_maps/hjmapdat_record0_explained.png')
print('saved record0 explained', im.size)

# ---- stats ----
terr=collections.Counter(B[i]&0xF for i in range(len(B)))
az=collections.Counter(A)
print('terrain type counts:', dict(sorted(terr.items())))
print('A cat counts:', dict(sorted(az.items())))
