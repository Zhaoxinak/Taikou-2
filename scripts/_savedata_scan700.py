import os
SRC="F:/Games/Taikou2"
def rd(n): return open(os.path.join(SRC,n),"rb").read()
s=rd("SAVEDATA.TR2")
L=len(s)
print("SAVEDATA len=%d"%L)

# ultra-strict: 700 consecutive bytes all in 0..91  (general->castle-code map)
hits=[]
i=0
while i+L-i>=0 and i<=L-700:
    ok=True
    for j in range(700):
        if s[i+j]>91:
            ok=False; i+=j+1; break
    if ok:
        hits.append(i); i+=700; continue
print("700B runs all in 0..91 (gen->castle map):", len(hits), hits[:10])

# also: 92 consecutive words all in 0..91 (castle owner code map)
def word_at(d,o): return d[o]|(d[o+1]<<8)
hits2=[]
i=0
while i+184<=L:
    ok=True
    for j in range(92):
        w=word_at(s,i+2*j)
        if w>91:
            ok=False; i+=1; break
    if ok:
        hits2.append(i); i+=2; continue
    i+=1
print("92-word runs all in 0..91 (castle owner):", len(hits2), hits2[:10])

# also: 700 consecutive bytes all in 0..699 won't happen (byte max 255). Try 700 words all in 0..699
hits3=[]
i=0
while i+1400<=L:
    ok=True
    for j in range(700):
        w=word_at(s,i+2*j)
        if w>699:
            ok=False; i+=1; break
    if ok:
        hits3.append(i); i+=2; continue
    i+=1
print("700-word runs all in 0..699 (gen-id array):", len(hits3), hits3[:10])

# dump context of first hit of each
for name,h in (("gen->castle(700B 0..91)",hits),("castle-owner(92W 0..91)",hits2)):
    if h:
        o=h[0]
        print("\n[%s] first hit @0x%x:"%(name,o))
        print("  bytes:", " ".join("%02x"%b for b in s[o:o+48]))
        if name.startswith("castle-owner"):
            ws=[word_at(s,o+2*j) for j in range(20)]
            print("  words:", ws)
