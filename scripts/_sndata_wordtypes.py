import json, os
from collections import defaultdict, Counter

BASE = os.path.dirname(os.path.abspath(__file__))
def load(p):
    with open(os.path.join(BASE, p), "r", encoding="utf-8") as f:
        return json.load(f)

rec = load("sndata_records.json")
ITEM = load("item_table.json")
items = {it["idx"]: it["name"] for it in ITEM}
SKILLS = [s["name"] for s in load("skill_master_table.json")["skills"]]  # 10
PROV = load("province_politics.json")["province_names"]
CITY = load("castle_town.json")
city_name = {c["idx"]: c["name"] for c in CITY}
ENT = load("bsdata_names.json")
ent_names = {"scenario1": ENT["BSDATA1"], "scenario2": ENT["BSDATA2"]}

CITY_N, ENT_N, PROV_N, ITEM_N, SK_N = 200, 700, 49, 189, 10

def rtype(r): return r["id_word"] & 0xff
groups = defaultdict(list)
for sc in ("scenario1","scenario2"):
    for r in rec[sc]["records"]:
        if r.get("real_byte_count",0)==0 and r.get("class")=="empty":
            continue
        groups[rtype(r)].append((sc, r))

def is_index_byte(v):
    return v <= ENT_N-1  # covers prov(<=48),city(<=199),ent(<=699)

print(f"{'type':>6} {'n':>3} {'bmin':>5} {'bmax':>5} {'bdist':>5} {'wmin':>6} {'wmax':>6} {'wdist':>5} {'item%':>5} {'sk%':>4} {'idx%':>5}  note")
candidate=[]
for t in sorted(groups):
    rows=groups[t]
    allbytes=[]; allwords=[]
    for sc,r in rows:
        pb=bytes.fromhex(r["payload_hex"])
        allbytes += list(pb)
        for i in range(0,len(pb)-1,2):
            allwords.append(pb[i] | (pb[i+1]<<8))
    if not allbytes: continue
    bmin,bmax=min(allbytes),max(allbytes)
    bdist=len(set(allbytes))
    wmin,wmax=min(allwords),max(allwords)
    wdist=len(set(allwords))
    item_hit=sum(1 for w in allwords if w<ITEM_N)
    sk_hit=sum(1 for w in allwords if w<SK_N)
    idx_hit=sum(1 for b in allbytes if is_index_byte(b))
    itemp=100*item_hit/len(allwords) if allwords else 0
    skp=100*sk_hit/len(allwords) if allwords else 0
    idxp=100*idx_hit/len(allbytes) if allbytes else 0
    # classify
    if idxp>70:
        note="LINKAGE(index mix)"
    elif itemp>80:
        note="WORD=ITEM?"
    elif skp>80:
        note="WORD=SKILL?"
    elif wmax<256 and bmax<256 and bdist<=20:
        note="byte-enum"
    elif wmax>=0x1000:
        note="word/large"
    else:
        note="misc"
    print(f"0x{t:02x} {len(rows):>3} {bmin:>5} {bmax:>5} {bdist:>5} {wmin:>6} {wmax:>6} {wdist:>5} {itemp:>4.0f}% {skp:>3.0f}% {idxp:>4.0f}%  {note}")
    if note in ("WORD=ITEM?","WORD=SKILL?","byte-enum","word/large","misc") and len(rows)>=5:
        candidate.append((t,rows,note))
