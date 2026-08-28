import os, json
SRC="F:/Games/Taikou2"
def rd(n): return open(os.path.join(SRC,n),"rb").read()
b=json.load(open("bsdata.json",encoding="utf-8"))["characters"]

for sc in (1,2):
    s=rd("SNDATA%d.TR2"%sc)
    key=s[0x12]^s[0x13]
    dec=bytes(x^key for x in s[0x598:])
    print("\n===== SNDATA%d  (dec stream len %d) ====="%(sc,len(dec)))
    # candidate A: 92-byte castle-owner array at 27040
    for off in (27040,27132):
        blk=dec[off:off+92]
        print(" castle? @%d (file 0x%x):"% (off,0x598+off), " ".join("%02x"%x for x in blk[:48]))
        print("    vals 0..91 all? ", all(x<=91 for x in blk), " distinct=",len(set(blk))," max=",max(blk))
    # candidate B: 700-word general array at 28042
    off=28042
    words=[dec[off+2*i]|(dec[off+2*i+1]<<8) for i in range(700)]
    print("\n general-idx array @%d (file 0x%x):"%(off,0x598+off))
    print("   first 40 words:", words[:40])
    print("   max=",max(words)," min=",min(words)," distinct=",len(set(words)))
    # cross-check with character names
    for idx in [0,13,16,27,100,300,699]:
        if idx<len(b):
            print("   word[%d]=%d  -> char[%d]=%s"%(idx,words[idx],words[idx], b[words[idx]].get('name','?') if words[idx]<len(b) else 'OUT'))
