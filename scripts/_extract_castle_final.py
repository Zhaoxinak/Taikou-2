import os, json
ROOT="F:/Games/Taikou 2"
STREAM_BASE=0x598      # decode base (XOR key = data[0x12]^data[0x13])
CASTLE_OFF=21845       # decoded-stream start of castle records (200 x 26B)  -- validated:
                        #   stream[0:2] (->rec+0x00) is a valid officer idx (<=369 / 0x172) for 199-200/200
                        #   (the 21852 "alignment" is a 7-byte slice artifact, see BREAKTHROUGHS 续97)
STRIDE=26
N=200

def u16(b,i): return b[i]|(b[i+1]<<8)
def decode(fn):
    data=open(os.path.join(ROOT,fn),'rb').read()
    key=data[0x12]^data[0x13]
    s=bytearray(data[STREAM_BASE:])
    for i in range(len(s)): s[i]^=key
    return key, bytes(s)

OFFICER_SENTINELS=(0x172, 0xffff)   # 370 = vacant, 65535 = undeveloped slot

def parse(d):
    eid=u16(d,0)
    return {
        "raw": list(d),
        # --- loader reads in order (0x47e130); stream[0:2] -> rec+0x00 resolved to ENTITY ptr (x47+0x519868) ---
        "lord_idx":  -1 if eid in OFFICER_SENTINELS else eid,   # stream[0:2] -> rec+0x00  = 城主/領主武将号 (x47 entity)
        "main_castle": d[2],                                    # stream[2]   -> rec+0x04  = 親城リンク (衛星->本城) 0..40, resolved to castle ptr
        "f08": d[3], "f09": d[4],                               # stream[3]/[4] -> rec+0x08/+0x09  state/type bytes
        "f0a": u16(d,5),                                        # stream[5:6] -> rec+0x0a  (2B, unknown)
        "agri_comm": d[7],                                      # stream[7]   -> rec+0x0c  = 農商 level (0..39)
        "sub_or_def": d[8],                                     # stream[8]   -> rec+0x0d  = 守城度/次级 (0..250)
        "order": d[9],                                          # stream[9]   -> rec+0x0e  = 民心 (0..39)
        "product": d[10],                                       # stream[10]  -> rec+0x0f  = 生産率 (0..250)
        "food": u16(d,11),                                      # stream[11:12]-> rec+0x10 = 軍糧
        "rice": u16(d,13),                                      # stream[13:14]-> rec+0x12 = 米
        "money": u16(d,15),                                     # stream[15:16]-> rec+0x14 = 資金
        "region": d[17],                                        # stream[17]  -> rec+0x16 (low) = 地域/地方 (0..14)
        "region_hi": d[18],                                     # stream[18]  -> rec+0x16 (high) = region flag (4/5)
        "unused_ffff": u16(d,19),                               # stream[19:20]-> rec+0x18 = 0xffff for ALL (unused sentinel)
        "f1a": d[21],                                           # stream[21]  -> rec+0x1a  (0..255)
        "type_word": u16(d,22),                                 # stream[22:23]-> rec+0x1b = 城種 (&7)
        "type": u16(d,22) & 7,
        "province": d[24],                                      # stream[24]  -> rec+0x1d (low) = 所属国 (0..48, 49 distinct)  *** TRUE province ***
        "province_hi": d[25],                                   # stream[25]  -> rec+0x1d (high) = subregion flag (0..15)
    }

res={}
for sc,fn in (("scenario1","Taikou2 Original/SNDATA1.TR2"),("scenario2","Taikou2 Original/SNDATA2.TR2")):
    key,s=decode(fn)
    lidx=[parse(s[CASTLE_OFF+STRIDE*i:CASTLE_OFF+STRIDE*i+26])["lord_idx"] for i in range(N)]
    prov=[parse(s[CASTLE_OFF+STRIDE*i:CASTLE_OFF+STRIDE*i+26])["province"] for i in range(N)]
    mc=[parse(s[CASTLE_OFF+STRIDE*i:CASTLE_OFF+STRIDE*i+26])["main_castle"] for i in range(N)]
    print(f"{sc}: key={key:#x}")
    print(f"  lord_idx valid(<=369 or sentinel)={sum(1 for v in lidx if v==-1 or 0<=v<=369)}/200  vacant/sentinel={sum(1 for v in lidx if v==-1)}")
    print(f"  province(byte24) min={min(prov)} max={max(prov)} distinct={len(set(prov))} all0..48={all(0<=p<=48 for p in prov)}")
    print(f"  main_castle(byte2) min={min(mc)} max={max(mc)} distinct={len(set(mc))} all<200={all(0<=v<200 for v in mc)}")
    reg=[parse(s[CASTLE_OFF+STRIDE*i:CASTLE_OFF+STRIDE*i+26])["region"] for i in range(N)]
    print(f"  region(byte17) min={min(reg)} max={max(reg)} distinct={len(set(reg))}")
    print(f"  unused_ffff(byte19:20) all_ffff={all(parse(s[CASTLE_OFF+STRIDE*i:CASTLE_OFF+STRIDE*i+26])['unused_ffff']==0xffff for i in range(N))}")
    castles=[]
    for i in range(N):
        d=s[CASTLE_OFF+STRIDE*i:CASTLE_OFF+STRIDE*i+26]
        c=parse(d); c["id"]=i
        castles.append(c)
    res[sc]=castles

json.dump(res, open("scripts/castle_values.json","w",encoding='utf-8'), ensure_ascii=False, indent=1)
print("\nwrote scripts/castle_values.json :", len(res["scenario1"]), "x2 scenarios")

print("\nscenario1 top-8 by money:")
for c in sorted(res["scenario1"], key=lambda x:-x["money"])[:8]:
    print(f"  id={c['id']:3d} lord={c['lord_idx']:4d} main={c['main_castle']:3d} region={c['region']:2d} "
          f"prov={c['province']:2d} money={c['money']:6d} rice={c['rice']:6d} food={c['food']:5d} type={c['type']}")
