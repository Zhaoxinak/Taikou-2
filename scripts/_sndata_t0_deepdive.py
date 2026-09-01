import json, os
from collections import defaultdict, Counter

BASE = os.path.dirname(os.path.abspath(__file__))
def load(p):
    with open(os.path.join(BASE, p), "r", encoding="utf-8") as f:
        return json.load(f)

rec = load("sndata_records.json")
CITY = load("castle_town.json")
ENT  = load("bsdata_names.json")
PROV = load("province_politics.json")["province_names"]

city_name = {c["idx"]: c["name"] for c in CITY}
ent_names = {"scenario1": ENT["BSDATA1"], "scenario2": ENT["BSDATA2"]}
CITY_N, ENT_N, PROV_N = 200, 700, 49

def rtype(r): return r["id_word"] & 0xff

groups = defaultdict(list)
for sc in ("scenario1","scenario2"):
    for r in rec[sc]["records"]:
        if r.get("real_byte_count",0)==0 and r.get("class")=="empty":
            continue
        groups[rtype(r)].append((sc, r))

print("distinct real types:", len(groups))
for t in sorted(groups, key=lambda t:-len(groups[t]))[:20]:
    print(f"  type=0x{t:02x}: {len(groups[t])} records")

def domain_of(v):
    if v==0: return "zero"
    if v<=1: return "bool"
    if v<=PROV_N-1: return "prov"
    if v<=CITY_N-1: return "city"
    if v<=ENT_N-1: return "ent"
    if v>=0x1000: return "word"
    return "byteenum"

def resname(sc, dom, v):
    if dom=="city": return city_name.get(v,"?")
    if dom=="ent": return ent_names[sc][v] if v<len(ent_names[sc]) else "?"
    if dom=="prov": return PROV[v] if v<len(PROV) else "?"
    return str(v)

print("\n===== TYPE 0x00 deep dive =====")
t0 = groups.get(0x00, [])
print("records:", len(t0))
if t0:
    pos_dom = defaultdict(Counter)
    samples=[]
    for sc,r in t0[:80]:
        pb=bytes.fromhex(r["payload_hex"])
        row=[]
        for i,b in enumerate(pb):
            d=domain_of(b); pos_dom[i][d]+=1
            row.append(resname(sc,d,b) if d in ("city","ent","prov") else (f"{b:02x}" if d!="zero" else "."))
        samples.append((sc,r["id_word"],r["sub_word"],row))
    print("per-position dominant domain:")
    for i in range(43):
        c=pos_dom[i]; tot=sum(c.values()); dom=c.most_common(1)[0]
        print(f"  pos{i:2d}: {dom[0]:9s} {dom[1]}/{tot}  {dict(c)}")
    print("\nfirst 8 records resolved:")
    for sc,iw,sw,row in samples[:8]:
        print(f"  [{sc} idw=0x{iw:04x} sub=0x{sw:04x}] " + " ".join(row))
