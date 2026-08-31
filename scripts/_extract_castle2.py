import json, struct, os

ROOT = "F:/Games/Taikou 2"
STREAM_BASE = 9612   # raw file offset where the decoded stream begins (emulation-confirmed)

def u16(b, i):
    return b[i] | (b[i+1] << 8)

def decode(fn):
    with open(fn, 'rb') as f:
        data = f.read()
    assert data[:16] == b'TAIKOU2_SCENARIO', fn
    key = data[0x12] ^ data[0x13]
    raw = data[STREAM_BASE:]
    stream = bytearray(raw)
    for i in range(len(stream)):
        stream[i] ^= key
    return key, bytes(stream)

KEY_BASE = 21852   # castle block decoded-stream offset (emulation: 31464-9612)
STRIDE = 26
N = 200

# stream byte -> runtime offset (from 0x47e130 disassembly, esi = 0x51eb8c = base+4)
# byte[0:2] WORD -> +0x00 entity idx (sentinel 0x172=370 => null)
# byte[2]   BYTE -> +0x04 self idx (0..199)
# byte[3]   BYTE -> +0x08
# byte[4]   BYTE -> +0x09
# byte[5:7] WORD -> +0x0a
# byte[7]   BYTE -> +0x0c
# byte[8]   BYTE -> +0x0d
# byte[9]   BYTE -> +0x0e
# byte[10]  BYTE -> +0x0f
# byte[11:13] WORD -> +0x10
# byte[13:15] WORD -> +0x12
# byte[15:17] WORD -> +0x14
# byte[17:19] WORD -> +0x16
# byte[19:21] WORD -> +0x18
# byte[21]  BYTE -> +0x1a
# byte[22:24] WORD -> +0x1b
# byte[24:26] WORD -> +0x1d

def parse(d):
    return {
        "entity_idx": u16(d, 0),
        "self_idx":   d[2],
        "b08": d[3],
        "b09": d[4],
        "w0a": u16(d, 5),
        "b0c": d[7],
        "b0d": d[8],
        "b0e": d[9],
        "b0f": d[10],
        "w10": u16(d, 11),
        "w12": u16(d, 13),
        "w14": u16(d, 15),
        "w16": u16(d, 17),
        "w18": u16(d, 19),
        "b1a": d[21],
        "w1b": u16(d, 22),
        "w1d": u16(d, 24),
        "type": u16(d, 22) & 7,
    }

res = {}
for sc, fn in (("scenario1", "Taikou2 Original/SNDATA1.TR2"),
               ("scenario2", "Taikou2 Original/SNDATA2.TR2")):
    key, s = decode(os.path.join(ROOT, fn))
    print(f"\n=== {sc}: XOR key=0x{key:02x}, stream len={len(s)} ===")
    # sanity: province@27052
    print(f"  province@27052 = {list(s[27052:27057])} (expect [5,0,64,28,0])")
    # sanity: castle self-idx sequential + entity valid
    sidx = [s[KEY_BASE+STRIDE*i+2] for i in range(N)]
    eids = [u16(s, KEY_BASE+STRIDE*i) for i in range(N)]
    print(f"  castle self-idx: min={min(sidx)} max={max(sidx)} sequential0..199={sidx==list(range(N))}")
    print(f"  castle entity_idx: min={min(eids)} max={max(eids)} sentinel0x172={sum(1 for e in eids if e==0x172)}")
    castles = []
    for i in range(N):
        d = s[KEY_BASE+STRIDE*i: KEY_BASE+STRIDE*i+26]
        c = parse(d); c["id"] = i
        castles.append(c)
    res[sc] = castles

# sanity dump famous castles (scenario1)
names = {0:"?",1:"?",2:"?",3:"?",4:"?",5:"小田原",6:"?",7:"?",8:"?",9:"?",
         10:"?",11:"?",12:"春日山(越後)",13:"駿府(駿河)",14:"浜松(遠江)",15:"岡崎(三河)",
         16:"清洲(尾張)",17:"稻葉山(美濃)",21:"金沢(加賀)",22:"一乗谷(越前)"}
print("\n=== scenario1 sample castles (raw extracted) ===")
for c in res["scenario1"]:
    if c["id"] in (5,12,13,14,15,16,17,21,22):
        nm = names.get(c["id"], "")
        print(f"  id={c['id']:3d} {nm:12s} self={c['self_idx']} ent={c['entity_idx']:4d} "
              f"b08={c['b08']:3d} b09={c['b09']:3d} w0a={c['w0a']:5d} b0c={c['b0c']:3d} b0d={c['b0d']:3d} "
              f"b0e={c['b0e']:3d} b0f={c['b0f']:3d} w10={c['w10']:5d} w12={c['w12']:5d} w14={c['w14']:5d} "
              f"w16={c['w16']:4d} w18={c['w18']:4d} b1a={c['b1a']:3d} w1b={c['w1b']:5d} w1d={c['w1d']:5d} type={c['type']}")

json.dump(res, open("scripts/castle_values.json", "w", encoding='utf-8'), ensure_ascii=False, indent=1)
print("\nwrote scripts/castle_values.json")
