import os
SRC = "F:/Games/Taikou2"
def rd(name):
    p = os.path.join(SRC, name)
    return open(p,"rb").read() if os.path.exists(p) else None

# 1) list all files with sizes
print("=== all .TR2 / data files in original ===")
for f in sorted(os.listdir(SRC)):
    p=os.path.join(SRC,f)
    if os.path.isfile(p):
        sz=os.path.getsize(p)
        if sz>1000:
            print("  %-22s %8d  (0x%05x)" % (f, sz, sz))

s1 = rd("SNDATA1.TR2")
print("\n=== SNDATA1.TR2 len = %d (0x%x) ===" % (len(s1), len(s1)))
print("header[0:16] =", s1[:16])
print("tail[last23] =", s1[-23:].hex())

# layout hypothesis A: 16B header + 833*49 records + 23 tail
rec=49; hdr=16; tail=23
n = (len(s1)-hdr-tail)//rec
print("\n[HDR+%d*%d+TAIL] => %d records, remainder=%d" % (n,rec,(len(s1)-hdr-tail)%rec))

# show first 3 records (offset 0x10)
print("\n--- first 3 records @0x10 (each 49B) ---")
for i in range(3):
    o=hdr+i*rec
    print("rec%d @0x%04x:"%(i,o), s1[o:o+rec].hex())

# 0x47d860 seek points
for idx in (0,1):
    o = idx*20480 + 0x198
    print("\n[0x47d860 idx=%d] seek offset = 0x%x (%d)  inFile=%s" % (idx,o,o, o<len(s1)))
    if o<len(s1):
        print("  bytes @0x%x:"%o, s1[o:o+0x40].hex())

# 0x47d890 record points for idx 0..10
print("\n--- 0x47d890 records idx 0..10 ---")
for idx in range(11):
    o=hdr+idx*rec
    print("rec%d @0x%x:"%(idx,o), s1[o:o+rec].hex())
