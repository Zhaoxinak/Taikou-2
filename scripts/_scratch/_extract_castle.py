# -*- coding: utf-8 -*-
"""Extract authoritative castle-table ground-truth values from disk SNDATA1/2.
Decrypt XOR stream (key=header[0x12]^header[0x13]); castle block @ stream 21852,
stride 26, 200 records. Map disk bytes -> runtime 0x51eb88 offsets via 0x47e130
(load serializer) + 3-byte tail (+0x09,+0x1a,+0x1e).
"""
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>

import os, json

BASE = _ROOT + '/Taikou2 Original'
OUT = _ROOT + '/scripts/castle_values.json'

def decode(path):
    raw = open(os.path.join(BASE, path), "rb").read()
    assert raw[:16] == b"TAIKOU2_SCENARIO", raw[:16]
    key = raw[0x12] ^ raw[0x13]
    stream = bytes(b ^ key for b in raw[0x598:])
    return stream

# disk[0:26] -> runtime field mapping (derived from 0x47e130 + tail serializer)
# d[0:2]=entity idx(ptr); d[2]=self idx(ptr); d[3]=+0x08; d[23]=+0x09(农商乘数);
# d[4:6]=+0x0a(城主); d[6]=+0x0c(农商等级); d[7]=+0x0d(守城度); d[8]=+0x0e(民心);
# d[9]=+0x0f(生产率); d[10:12]=+0x10(军粮); d[12:14]=+0x12(米); d[14:16]=+0x14(资金);
# d[16:18]=+0x16; d[18]=+0x18; d[24]=+0x1a(次级民情); d[19:21]=+0x1b(城种);
# d[21:23]=+0x1d; d[25]=+0x1e
def parse_castle(d, tail):
    def u16(a, b): return a | (b << 8)
    return {
        "ent_idx": u16(d[0], d[1]),
        "self_idx": d[2],
        "f08": d[3],                       # unknown
        "agri_comm_mul": tail[0],          # +0x09 农商乘数 (tail block)
        "lord_id": u16(d[4], d[5]),        # +0x0a 城主武将编号
        "agri_comm_lv": d[6],              # +0x0c 农商等级
        "def_lv": d[7],                    # +0x0d 守城度/次级等级
        "pub_order": d[8],                 # +0x0e 民心
        "productivity": d[9],              # +0x0f 生产率
        "food": u16(d[10], d[11]),         # +0x10 军粮
        "rice": u16(d[12], d[13]),         # +0x12 米
        "money": u16(d[14], d[15]),        # +0x14 资金
        "f16": u16(d[16], d[17]),          # +0x16 unknown
        "f18": d[18],                      # +0x18 unknown
        "sub_mood": tail[1],               # +0x1a 次级民情 (tail block)
        "type_word": u16(d[19], d[20]),    # +0x1b 城种 (low3 bits)
        "f1d": u16(d[21], d[22]),          # +0x1d unknown
        "f1e": tail[2],                    # +0x1e unknown (tail block)
        "type": u16(d[19], d[20]) & 7,
    }

names = json.load(open(_ROOT + '/scripts/castle_names.json', encoding='utf-8'))["castles"]
name_by_id = {c["id"]: c for c in names}

res = {}
for sc, fn in (("scenario1", "SNDATA1.TR2"), ("scenario2", "SNDATA2.TR2")):
    stream = decode(fn)
    # main: 23 bytes/castle, stride 23, from 21852 -> 26452
    main = stream[21852:21852 + 200 * 23]
    # tail: 3 bytes/castle, stride 3, from 26452 -> 27052 (= verified province)
    tail = stream[26452:26452 + 200 * 3]
    castles = []
    for i in range(200):
        d = main[i * 23:(i + 1) * 23]
        t = tail[i * 3:(i + 1) * 3]
        c = parse_castle(d, t)
        nm = name_by_id.get(i, {})
        c["id"] = i
        c["code_hex"] = nm.get("hex")
        c["name"] = nm.get("display") or nm.get("name")
        castles.append(c)
    res[sc] = castles

# verification stats
for sc, cs in res.items():
    lord = [c["lord_id"] for c in cs]
    money = [c["money"] for c in cs]
    print(f"\n## {sc}: {len(cs)} castles")
    print(f"  lord_id range: min={min(lord)} max={max(lord)} (0xffff count={sum(1 for x in lord if x==0xffff)})")
    print(f"  lord_id in 0..699: {sum(1 for x in lord if 0<=x<=699)} / 0xffff: {sum(1 for x in lord if x==0xffff)} / other: {sum(1 for x in lord if not(0<=x<=699) and x!=0xffff)}")
    print(f"  money range: min={min(money)} max={max(money)} (0xffff count={sum(1 for x in money if x==0xffff)})")
    print(f"  agri_comm_mul range: {min(c['agri_comm_mul'] for c in cs)}..{max(c['agri_comm_mul'] for c in cs)}")
    print(f"  type distribution: {sorted(set(c['type'] for c in cs))}")
    # show a few occupied-looking castles (lord in 0..699)
    occ = [c for c in cs if 0 <= c["lord_id"] <= 699][:5]
    for c in occ:
        print(f"    id={c['id']} {c['name']}: lord={c['lord_id']} money={c['money']} food={c['food']} rice={c['rice']} agri_comm_lv={c['agri_comm_lv']} def_lv={c['def_lv']} pub_order={c['pub_order']} type={c['type']}")

json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\nWROTE {OUT}")
