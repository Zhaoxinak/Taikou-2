import struct

BIN = r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
data = open(BIN, "rb").read()
print("bin size", len(data), hex(len(data)))

# Known battle-related absolute addresses to hunt for (as 4-byte LE immediates)
targets = {
    0x503740: "diff-table-A (variant/HJMAPDAT)",
    0x503750: "diff-table-B",
    0x512f10: "char->sprite map table",
    0x505c00: "battle tile palette base",
    0x505c8c: "battle tile palette (aligned)",
    0x519288: "700B general flags (runtime)",
    0x522c88: "scenario state buf (castles/gens)",
    0x522ce4: "92-castle 1B array",
    0x5179b8: "name/src table stride14 370 (gen)",
    0x506ca8: "name table 370 (prov/castle/type)",
}

hits = {t: [] for t in targets}
for t, label in targets.items():
    pat = struct.pack("<I", t)
    start = 0
    while True:
        i = data.find(pat, start)
        if i < 0:
            break
        hits[t].append(BASE + i)
        start = i + 1

for t, label in targets.items():
    hs = hits[t]
    print(f"\n=== 0x{t:06x} {label}: {len(hs)} hits ===")
    for h in hs[:25]:
        print(f"   ref @ VA 0x{h:06x}")
