import struct

BIN = r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
data = open(BIN, "rb").read()

# ---- dump 0x503770 .. 0x504000 as u8 and u16 ----
print("="*70)
print("0x503770 .. 0x504000  (candidate battle stat region)")
print("="*70)
off = 0x503770 - BASE
blk = data[off:off+0x290]
# print as u16 rows (16 per row), safe against short last row
for i in range(0, len(blk)-31, 32):
    u16 = struct.unpack("<16H", blk[i:i+32])
    print(f"{0x503770+i:06x}  u16: {list(u16)}")
print()
print("---- same region as u8 (compact) ----")
for i in range(0, len(blk), 24):
    print(f"{0x503770+i:06x}  " + " ".join(f"{x:3d}" for x in blk[i:i+24]))

# ---- search for unit-type / formation / stratagem GBK strings ----
print("\n"+"="*70)
print("GBK string search for battle vocabulary")
print("="*70)
terms = {
    "足轻": b"\xd7\xe1\xc7\xe1",
    "骑兵": b"\xc6\xbd\xb1\xed",
    "铁炮": b"\xcc\xfa\xc5\xa9",
    "弓":   b"\xb9\xdd",
    "攻城": b"\xb9\xa5\xb3\xf6",
    "水军": b"\xcb\xae\xbe\xfc",
    "阵形": b"\xd5\xfb\xd0\xce",
    "鹤翼": b"\xba\xd7\xd2\xcc",
    "鱼鳞": b"\xd3\xe3\xc1\xdb",
    "火计": b"\xbb\xf0\xbc\xc6",
    "伏兵": b"\xb7\xb8\xb1\xf8",
    "落石": b"\xc2\xe4\xca\xaf",
    "齐射": b"\xc6\xeb\xc9\xe8",
    "突撃": b"\xc4\xab\xbb\xf7",
}
for name, pat in terms.items():
    idx = 0
    hits = []
    while True:
        j = data.find(pat, idx)
        if j < 0: break
        hits.append(BASE + j)
        idx = j + 1
    if hits:
        print(f"  {name}: {len(hits)} hits, e.g. VA 0x{hits[0]:06x}")
    else:
        print(f"  {name}: (not found)")
