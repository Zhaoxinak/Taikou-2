import os, struct, collections
D="/Users/ts/Downloads/Taikou 2/Taikou2 Original"
def rd(n): return open(os.path.join(D,n),'rb').read()

print("="*70)
print("A. 三个 128006 文件：头 6B + 128000B 载荷")
for n in ("ACERTWP.GRP","KOEILOGO.GRP","PRESS.GRP"):
    b=rd(n); h=struct.unpack("<3H", b[:6]); body=b[6:]
    print(n, "hdr(u16LE)=", h, "len(body)=",len(body))
    # 4-byte group pattern
    groups=collections.Counter(body[i:i+4] for i in range(0,len(body),4))
    print("   distinct 4B groups:", len(groups), "top:", [(g.hex(),c) for g,c in groups.most_common(4)])
    print("   distinct bytes:", len(set(body)), sorted(set(body))[:16])

print("="*70)
print("B. SMODE.GRP")
b=rd("SMODE.GRP"); print("len", len(b))
# 4-byte group pattern in first N
n4=0
for i in range(0,0x2000,4):
    g=b[i:i+4]
    if g[2]==0 and g[1]==g[3]: n4+=1
print("首 0x2000 内符合 [A,B,00,B] 的 4B 组:", n4, "/", 0x2000//4)
# tail: palette check
for palsz in (768,1024):
    for endoff in (0,1,2,3):
        p=b[len(b)-endoff-palsz:len(b)-endoff]
        if len(p)!=palsz: continue
        if palsz==1024:
            ok=sum(1 for i in range(0,1024,4) if p[i+3]==0)
            print(f"  tail palette 1024 @end-{endoff}: reserved==0 count {ok}/256")
        else:
            print(f"  tail 768 @end-{endoff}: max={max(p)}")
print("  last 8 bytes:", b[-8:].hex())
print("="*70)
print("C. END.GRP big-endian offset table?")
b=rd("END.GRP"); print("len",len(b))
first=struct.unpack(">I", b[:4])[0]
print("first BE u32 =", first, hex(first))
nent=first//4
offs=[struct.unpack(">I", b[4*i:4*i+4])[0] for i in range(nent)]
mono=all(offs[i]<offs[i+1] for i in range(len(offs)-1))
print("entries",nent,"monotonic increasing:",mono,"last off",hex(offs[-1]),"filelen",hex(len(b)))
print("first 8:", [hex(x) for x in offs[:8]])
print("last 4:", [hex(x) for x in offs[-4:]])
print("tail 16:", b[-16:], b[-16:].hex())
# subimage header at each offset
print("sub-image heads:")
for i in range(6):
    o=offs[i]; print("  ", i, hex(o), b[o:o+12].hex(), "u16LE", struct.unpack("<6H", b[o:o+12]))
print("="*70)
print("D. EXTFACE.PK8")
b=rd("EXTFACE.PK8"); print("len",len(b), "hdr u16LE", struct.unpack("<4H", b[:8]))
print(b[:48].hex())
