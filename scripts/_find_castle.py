import os, json
ROOT="F:/Games/Taikou 2"
def decode(fn):
    data=open(os.path.join(ROOT,fn),'rb').read()
    key=data[0x12]^data[0x13]
    s=bytearray(data[0x598:])
    for i in range(len(s)): s[i]^=key
    return key, bytes(s)

def u16(b,i): return b[i]|(b[i+1]<<8)

for sc,fn in (("sc1","Taikou2 Original/SNDATA1.TR2"),("sc2","Taikou2 Original/SNDATA2.TR2")):
    key,s=decode(fn)
    print(f"\n=== {sc}: key=0x{key:02x} len={len(s)} ===")
    # search for 200-record block, stride 26, where every record:
    #  entity_idx (WORD@0) in [0,370] or ==0x172(sentinel)
    #  self_idx (BYTE@2) in [0,199]
    best=[]
    for base in range(0, len(s)-26*200):
        ok=0; seq=0
        for i in range(200):
            e=u16(s, base+26*i)
            si=s[base+26*i+2]
            if (e<=370 or e==0x172) and si<=199:
                ok+=1
            if si==i: seq+=1
        if ok>=199:
            best.append((ok,seq,base))
    best.sort(reverse=True)
    print("candidates (ok,seq,base) with >=199 valid records:")
    for c in best[:15]:
        print("  ",c)
    if best:
        base=best[0][2]
        print(f"\n-> using base={base}; first 4 castle records @decoded {base}:")
        for i in range(4):
            d=s[base+26*i:base+26*i+26]
            print(f"  rec{i}: ent={u16(d,0):4d} self={d[2]:3d} b3={d[3]:3d} b4={d[4]:3d} w0a={u16(d,5):5d} b7={d[7]:3d} b8={d[8]:3d} b9={d[9]:3d} "
                  f"b10={d[10]:3d} w10={u16(d,11):5d} w12={u16(d,13):5d} w14={u16(d,15):5d} w16={u16(d,17):4d} w18={u16(d,19):4d} "
                  f"b1a={d[21]:3d} w1b={u16(d,22):5d} w1d={u16(d,24):5d}")
