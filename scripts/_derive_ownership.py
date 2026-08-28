#!/usr/bin/env python3
"""Derive castle ownership + general loyalty tree from decoded BSDATA + SAVEDATA
gen-flags, and decode the EXE castle/province name table at 0x506ca8.
Outputs scripts/ownership_derived.json (castle -> owner/occupants; general -> castle/lord).
NOTE: this is the ROSTER-based baseline (historical home_city + status). The scenario
save file may override specific placements; see SAVEDATA runtime buffers for that.
"""
import json, struct, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SC = os.path.join(ROOT, "scripts")
BIN = os.path.join(SC, "_unpacked_mem.bin")
BASE = 0x400000

# ---- 1. decode EXE name table at 0x506ca8 (370 entries, try stride 14) ----
data = open(BIN, "rb").read()
def dec_gbk(b):
    return b.split(b"\x00",1)[0].decode("gbk","replace").strip()
names = []
for i in range(370):
    off = (0x506ca8 - BASE) + i*14
    chunk = data[off:off+14]
    names.append(dec_gbk(chunk))
print("name table sample:", names[:6], "...", names[49:53], "...", names[292:295])
province_names = names[0:49]
castle_names   = names[49:49+92]   # 92 castles (if table lays out 49 prov + 92 castle + 78 type)
print("castle[0..4]:", castle_names[:5], " n_castle_raw=", len([n for n in castle_names if n]))

# ---- 2. load BSDATA ----
bs = json.load(open(os.path.join(SC, "bsdata.json")))
chars = bs["characters"]

# ---- 3. SAVEDATA gen-flags (present mask) ----
sd = open(r"F:/Games/Taikou2/SAVEDATA.TR2","rb").read()
present = sd[0x1ac:0x1ac+700]

# validate home_city range
hc = [c["home_city"] for c in chars]
print("home_city distinct:", len(set(hc)), "min", min(hc), "max", max(hc), "max<92?", max(hc) < 92)

# ---- 4. build occupancy + ownership ----
castle_occ = {c: [] for c in range(92)}
for g in chars:
    cid = g["id"]
    if present[cid] != 1:
        continue
    hc_v = g["home_city"]
    if 0 <= hc_v < 92:
        castle_occ[hc_v].append(g)

def owner_of(occupants):
    # owner = a 大名 (status 7); else highest status
    daim = [g for g in occupants if g["status"] == 7]
    if daim:
        return max(daim, key=lambda g: g["forces"].get("统率",0))
    if occupants:
        return max(occupants, key=lambda g: (g["status"], g["forces"].get("统率",0)))
    return None

castle_tbl = {}
for c in range(92):
    occ = castle_occ[c]
    ow = owner_of(occ)
    castle_tbl[c] = {
        "castle_name": castle_names[c] if c < len(castle_names) else f"城{c}",
        "owner_id": ow["id"] if ow else None,
        "owner_name": ow["name"] if ow else None,
        "occupant_ids": [g["id"] for g in occ],
        "occupant_names": [g["name"] for g in occ],
    }

# general -> (castle, lord)
gen_tbl = {}
for g in chars:
    cid = g["id"]
    if present[cid] != 1:
        continue
    c = g["home_city"]
    ow = owner_of(castle_occ.get(c, []))
    gen_tbl[cid] = {
        "name": g["name"],
        "castle_id": c,
        "castle_name": castle_names[c] if 0 <= c < len(castle_names) else f"城{c}",
        "status": g["status"],
        "lord_id": ow["id"] if (ow and ow["id"] != cid) else None,
        "lord_name": ow["name"] if (ow and ow["id"] != cid) else None,
    }

owns = [v for v in castle_tbl.values() if v["owner_id"] is not None]
print(f"castles with owner: {len(owns)}/92 ; generals placed: {len(gen_tbl)}")
# sample
for c in list(castle_tbl)[:5]:
    v = castle_tbl[c]
    print(f"  城{c} {v['castle_name']}: 主 {v['owner_name']} 驻 {v['occupant_names'][:4]}")

out = {
    "method": "derived from BSDATA home_city@49 + status@57, filtered by SAVEDATA gen-flags(0x1ac)",
    "caveat": "roster baseline; scenario save may override; runtime buffers 0x522c60/0x522c70/0x522ca0 hold live state",
    "castle_count_with_owner": len(owns),
    "castles": castle_tbl,
    "generals": gen_tbl,
}
json.dump(out, open(os.path.join(SC, "ownership_derived.json"),"w",encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("wrote ownership_derived.json")
