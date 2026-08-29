import os
SRC="F:/Games/Taikou2"
def rd(n):
    p=os.path.join(SRC,n); return open(p,"rb").read() if os.path.exists(p) else None

# check if SAVEDATA exists
for cand in ["SAVEDATA.TR2","SAVEDATA1.TR2","GENERAL.TR2","SNDATA3.TR2"]:
    print("exist %s : %s" % (cand, os.path.exists(os.path.join(SRC,cand))))

s1=rd("SNDATA1.TR2")
L=len(s1)
print("\nSNDATA1 len=%d (0x%x)"%(L,L))
print("header:",s1[:16])
print("tail23 :",s1[-23:].hex())

rec,head,tail=49,16,23
nfull=(L-head-tail)//rec
print("records(fit)=",nfull,"rem=",(L-head-tail)%rec)

print("\n-- first 3 records @0x10 --")
for i in range(3):
    o=head+i*rec
    print(" r%d@0x%04x:"%(i,o), s1[o:o+rec].hex())

print("\n-- 0x47d860 seek blocks --")
for idx in (0,1):
    o=idx*20480+0x198
    ok = o+64<=L
    print(" idx%d off=0x%05x inFile=%s"%(idx,o,ok))
    if ok: print("   ",s1[o:o+64].hex())

print("\n-- 0x47d890 records idx 0..5 --")
for idx in range(6):
    o=head+idx*rec
    print(" r%d@0x%04x:"%(idx,o), s1[o:o+rec].hex())

# Does 0x198 region look like a 'scene block' distinct from records?
# show record 8 boundary (0x10+8*49 = 0x198)
print("\nrecord index at 0x198 =", (0x198-head)//rec, " (0x198-head=%d)"%(0x198-head))
