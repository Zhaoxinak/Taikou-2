import os, json
ROOT="F:/Games/Taikou 2"
STREAM_BASE=0x598          # decode start
CASTLE_OFF=21845           # decoded-stream offset of castle block (empirically validated)
STRIDE=26
N=200

def u16(b,i): return b[i]|(b[i+1]<<8)
def decode(fn):
    data=open(os.path.join(ROOT,fn),'rb').read()
    key=data[0x12]^data[0x13]
    s=bytearray(data[STREAM_BASE:])
    for i in range(len(s)): s[i]^=key
    return key, bytes(s)

def parse(d):
    eid=u16(d,0)
    return {
        "officer_idx": -1 if eid==0x172 else eid,   # byte[0:2] WORD -> 武将指针 source
        "parent_castle": d[2],                       # byte[2] BYTE  -> self-ptr target (main/satellite link)
        "b08": d[3],
        "b09": d[4],
        "w0a": u16(d,5),                             # byte[5:7] WORD
        "b0c": d[7],
        "b0d": d[8],
        "b0e": d[9],
        "b0f": d[10],
        "w10": u16(d,11),                            # byte[11:13] WORD
        "w12": u16(d,13),                            # byte[13:15] WORD
        "w14": u16(d,15),                            # byte[15:17] WORD
        "w16": u16(d,17),                            # byte[17:19] WORD
        "w18": u16(d,19),                            # byte[19:21] WORD  (-> 城主?)
        "b1a": d[21],
        "w1b": u16(d,22),                            # byte[22:24] WORD (low3 = 城种)
        "w1d": u16(d,24),                            # byte[24:26] WORD
        "type": u16(d,22)&7,
    }

res={}
for sc,fn in (("scenario1","Taikou2 Original/SNDATA1.TR2"),("scenario2","Taikou2 Original/SNDATA2.TR2")):
    key,s=decode(fn)
    print(f"\n=== {sc}: key=0x{key:02x} stream_len={len(s)} ===")
    # validation
    eids=[u16(s,CASTLE_OFF+STRIDE*i) for i in range(N)]
    pars=[s[CASTLE_OFF+STRIDE*i+2] for i in range(N)]
    valid_eid=sum(1 for e in eids if e<=370 or e==0x172)
    valid_par=sum(1 for p in pars if p<200)
    print(f"  castle block [{CASTLE_OFF}, {CASTLE_OFF+STRIDE*N})  valid_officer_idx={valid_eid}/200  valid_parent<200={valid_par}/200")
    print(f"  province@27052 = {list(s[27052:27057])}  (expect [5,0,64,28,0])")
    print(f"  7 bytes between castle-end and province: {list(s[CASTLE_OFF+STRIDE*N:27052])}")
    castles=[]
    for i in range(N):
        d=s[CASTLE_OFF+STRIDE*i:CASTLE_OFF+STRIDE*i+26]
        c=parse(d); c["id"]=i
        castles.append(c)
    res[sc]=castles

# Identify famous castles by cross-referencing known officers (lord) if possible.
# Dump first 12 and a few likely-major castles (high money w14)
print("\n=== scenario1: first 12 castles (slot, officer, parent, w10,w12,w14,w16,w18,type) ===")
for c in res["scenario1"][:12]:
    print(f"  id={c['id']:3d} off={c['officer_idx']:4d} par={c['parent_castle']:3d} "
          f"w10={c['w10']:5d} w12={c['w12']:5d} w14={c['w14']:6d} w16={c['w16']:4d} w18={c['w18']:4d} b1a={c['b1a']:3d} type={c['type']}")

json.dump(res, open("scripts/castle_values.json","w",encoding='utf-8'), ensure_ascii=False, indent=1)
print("\nwrote scripts/castle_values.json  (", len(res["scenario1"]), "castles x2 scenarios )")
