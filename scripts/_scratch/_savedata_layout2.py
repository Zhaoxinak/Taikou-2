import os, json
SRC="F:/Games/Taikou2"
def rd(n): return open(os.path.join(SRC,n),"rb").read()
s=rd("SAVEDATA.TR2")
print("len",len(s))
b=json.load(open("bsdata.json",encoding="utf-8"))["characters"]
# 0x198 scene block, 0x1ac 700B general array, 0x48c onward castle region
print("0x198 (scene block head):", s[0x198:0x198+32].hex())
gen=s[0x1ac:0x1ac+700]
print("\n0x1ac 700B gen-flags: first 40:", " ".join("%02x"%x for x in gen[:40]))
print("  distinct:",len(set(gen))," vals:",sorted(set(gen))[:10]," count1=",gen.count(1)," count0=",gen.count(0))
for idx in [0,13,16,27]:
    print("  gen[%d]=%d  (%s)"%(idx,gen[idx],b[idx].get('name','?') if idx<len(b) else '?'))
# castle region after gen array
for off in (0x48c, 0x48c+184, 0x48c+368):
    blk=s[off:off+92]
    print("\n@0x%x (92B):"%off, " ".join("%02x"%x for x in blk[:46]))
    print("   vals0..91?", all(x<=91 for x in blk), "max",max(blk))
# try 92-word castle array at 0x48c
ws=[s[0x48c+2*j]|(s[0x48c+2*j+1]<<8) for j in range(92)]
print("\n0x48c 92 words:", ws[:30], " max",max(ws)," min",min(ws)," distinct",len(set(ws)))
