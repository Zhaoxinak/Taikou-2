import os
SRC="F:/Games/Taikou2"
def rd(n): return open(os.path.join(SRC,n),"rb").read()

for sc in (1,2):
    s=rd("SNDATA%d.TR2"%sc)
    key = s[0x12]^s[0x13]   # obj[0x94] = byte0^byte1 (the XOR key)
    enc = s[0x598:]
    dec = bytes(b^key for b in enc)
    print("\n===== SNDATA%d  key=0x%02x  enc_len=%d ====="%(sc,key,len(enc)))
    print("decrypted head (0x598..):", dec[:96].hex())
    # ascii-ish view of first 64 bytes
    asc="".join(chr(b) if 32<=b<127 else '.' for b in dec[:96])
    print("  ascii:", asc)
    # value range
    from collections import Counter
    c=Counter(dec)
    print("  byte range: min=%d max=%d distinct=%d"%(min(dec),max(dec),len(c)))
    # scan for a run of 92 bytes each in 0..91 (castle ownership array)
    N=len(dec); found=[]
    i=0
    while i < N-92:
        ok=True
        for j in range(92):
            if dec[i+j]>91: ok=False; break
        if ok:
            found.append(i)
            i+=92; continue
        i+=1
    print("  runs of 92 bytes all in 0..91 (castle-owner candidates):", found[:10], "count=",len(found))
    # scan for a run of word-values all in 0..699 (general id array)
    wfound=[]
    i=0
    while i < N-700*2:
        ok=True
        for j in range(700):
            w=dec[i+2*j]|(dec[i+2*j+1]<<8)
            if w>700: ok=False; break
        if ok:
            wfound.append(i); break
        i+=1
    print("  word-run all in 0..699 (general-id candidate):", wfound[:5])
    # also: bytes 0..N print a histogram of top values in first 4096
    c2=Counter(dec[:4096])
    print("  top values in first 4096:", c2.most_common(12))
