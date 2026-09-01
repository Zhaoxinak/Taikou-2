
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
import json, struct

def u16(a,b): return a|(b<<8)

def decode(fn):
    with open(fn,'rb') as f: data=f.read()
    assert data[:16]==b'TAIKOU2_SCENARIO', fn
    key = data[0x12]^data[0x13]
    stream = bytearray(data[0x598:])
    for i in range(len(stream)): stream[i]^=key
    return key, bytes(stream)

KEY_BASE = 21852   # castle block stream offset (relative to 0x598)
STRIDE  = 26
N       = 200

# stream position within a record -> runtime offset (from 0x47e130 disassembly)
#  [0:2]  -> +0x00 entity ptr (idx, sentinel 0x172=370 => null)
#  [2]    -> +0x04 castle self ptr (idx 0..199, sentinel 0xc8=200 => null)
#  [3]    -> +0x08
#  [4]    -> +0x09  农商乘数
#  [5:7]  -> +0x0a  城主? (WORD)
#  [7]    -> +0x0c  农商等级
#  [8]    -> +0x0d  守城度/次级
#  [9]    -> +0x0e  民心
#  [10]   -> +0x0f  生产率
#  [11:13]-> +0x10  军粮
#  [13:15]-> +0x12  米
#  [15:17]-> +0x14  资金
#  [17:19]-> +0x16  所属国
#  [19]   -> +0x18  城主 (per cont78/79)
#  [20]   -> +0x1a  次级民情
#  [21:23]-> +0x1b  城种 (low3)
#  [23:25]-> +0x1d
#  [25]   -> (unused by loader)

def parse(d):
    return {
        "entity_idx": u16(d[0],d[1]),
        "self_idx":   d[2],
        "f08": d[3],
        "agri_comm_mul": d[4],
        "lord_w": u16(d[5],d[6]),
        "agri_comm_lv": d[7],
        "def_lv": d[8],
        "pub_order": d[9],
        "productivity": d[10],
        "food": u16(d[11],d[12]),
        "rice": u16(d[13],d[14]),
        "money": u16(d[15],d[16]),
        "province": d[17],   # +0x16 所属国
        "lord_b": d[19],     # +0x18 城主 (1B)
        "sub_mood": d[20],
        "type_word": u16(d[21],d[22]),
        "f1d": u16(d[23],d[24]),
        "type": u16(d[21],d[22]) & 7,
    }

res={}
for sc, fn in (("scenario1",_ROOT + '/Taikou2 Original/SNDATA1.TR2'),("scenario2",_ROOT + '/Taikou2 Original/SNDATA2.TR2')):
    key, s = decode(fn)
    print(f"\n=== {sc}: XOR key=0x{key:02x}, stream len={len(s)} ===")
    # brute-force search for 200 records where a byte position increments 0..199
    found=None
    for S in range(24,34):
        for P in range(6):
            for base in range(0, len(s)-S*200, 1):
                cnt=sum(1 for i in range(200) if base+S*i+P < len(s) and s[base+S*i+P]==i)
                if cnt>=199:
                    print(f"  MATCH S={S} P={P} base={base} cnt={cnt}  (block ends {base+S*200})"); found=(S,P,base); break
            if found: break
        if found: break
    if not found:
        print("  no sequential 0..199 self-index found (strides 24..33, pos 0..5)")
    # entity sentinel check fallback near 21852
    ents=[u16(s[KEY_BASE+STRIDE*i],s[KEY_BASE+STRIDE*i+1]) for i in range(N)]
    print(f"  [21852/26] entity_idx range min={min(ents)} max={max(ents)}; 0x172 sentinel count={sum(1 for e in ents if e==0x172)}")
    castles=[]
    for i in range(N):
        d=s[KEY_BASE+STRIDE*i : KEY_BASE+STRIDE*i+26]
        c=parse(d); c["id"]=i; castles.append(c)
    res[sc]=castles

# dump famous castles scenario1
names={0:"踯躅崎(甲斐)",16:"清洲(尾张)",17:"稻叶山(美浓)",21:"金沢(加賀)",
       14:"浜松(遠江)",15:"岡崎(三河)",13:"駿府(駿河)",12:"春日山(越後)",
       22:"一乗谷(越前)",10:"躑躅崎",11:"小田原?"}
print("\n=== scenario1 sample castles ===")
for c in res["scenario1"]:
    if c["id"] in (0,16,17,21,14,15,13,12,22):
        print(f"  id={c['id']:3d} self={c['self_idx']} ent={c['entity_idx']:4d} lord_w={c['lord_w']:4d} lord_b={c['lord_b']:3d} "
              f"prov={c['province']} money={c['money']:5d} food={c['food']:5d} rice={c['rice']:6d} "
              f"agri_lv={c['agri_comm_lv']} def_lv={c['def_lv']} pub={c['pub_order']} prod={c['productivity']} "
              f"agri_mul={c['agri_comm_mul']} type={c['type']} sub_mood={c['sub_mood']} f1d={c['f1d']}")

json.dump(res, open(_ROOT + '/scripts/castle_values.json',"w",encoding='utf-8'), ensure_ascii=False, indent=1)
print("\nwrote scripts/castle_values.json")
