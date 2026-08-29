import os
SRC="F:/Games/Taikou2"
def rd(n): return open(os.path.join(SRC,n),"rb").read()
s=rd("SAVEDATA.TR2")
L=len(s)
print("SAVEDATA len=%d (0x%x)"% (L,L))
print("header 16:", s[:16])
print("header 32:", s[:32].hex())

# check encryption: byte value distribution in first 4096
from collections import Counter
c=Counter(s[:4096])
print("first4k distinct:",len(c)," top:",c.most_common(6))
# if a single value dominates (like 0x0c/0x0a) -> encrypted
dom=c.most_common(1)[0]
print("dominant byte in first4k:",dom)

# Try to find 92-byte castle-owner arrays (each byte 0..91) anywhere
def find_runs(data, runlen, maxval, step=1):
    res=[]
    i=0
    while i < len(data)-runlen:
        ok=True
        for j in range(runlen):
            if data[i+j]>maxval: ok=False; break
        if ok:
            res.append(i); i+=runlen; continue
        i+=1
    return res

r92=find_runs(s, 92, 91)
print("\n92-byte runs all 0..91 (castle owner candidates):", len(r92), r92[:15])

# find 700-word arrays all in 0..699
def find_word_runs(data, n, maxval):
    res=[]; i=0
    while i+2*n <= len(data):
        ok=True
        for j in range(n):
            w=data[i+2*j]|(data[i+2*j+1]<<8)
            if w>maxval: ok=False; break
        if ok:
            res.append(i); i+=2; continue
        i+=1
    return res
r700=find_word_runs(s, 700, 699)
print("700-word runs all 0..699 (general-id candidates):", len(r700), r700[:10])

# Also check: is SAVEDATA laid out as 49B records? scan header for record marker
# dump a few regions
for off in [0x10, 0x198, 0x500, 0x1000, 0x2000]:
    if off+16<=L:
        print("  @0x%x:"%off, s[off:off+16].hex())
