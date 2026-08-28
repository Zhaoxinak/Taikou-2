import struct
from collections import Counter

DAT = r"F:/Games/Taikou2/HJMAPDAT.DAT"
data = open(DAT, "rb").read()
print("HJMAPDAT size", len(data), "= 38 x", len(data)//38, "(rec size)")
RECSZ = len(data) // 38
AHEAD, BTER, CDEP = 180, 760, 760  # A head / B terrain / C deploy

# B terrain: 40 cols x 19 rows, 1 nibble per cell (760 bytes = 1520 nibbles = 40*19*2)
all_terr = Counter()
per_rec = []
for r in range(38):
    rec = data[r*RECSZ: r*RECSZ+RECSZ]
    bsec = rec[AHEAD:AHEAD+BTER]
    cells = []
    for byte in bsec:
        cells.append(byte & 0xF)
        cells.append((byte >> 4) & 0xF)
    # 40x19 = 760 cells; cells has 1520 -> take first 760 (stride assumed row-major nibbles)
    cells = cells[:760]
    c = Counter(cells)
    per_rec.append(c)
    all_terr.update(cells)

print("\nGlobal terrain-nibble distribution (0-15) across all 38 maps (760 cells each):")
for t in range(16):
    print(f"  terrain {t:2d}: {all_terr.get(t,0):6d} cells  ({100*all_terr.get(t,0)/(38*760):.1f}%)")

# modifier high nibble distribution (B section stored as (modifier<<4)|terrain)
print("\nModifier(high nibble) distribution in B section (terrain=low nibble per byte):")
modc = Counter()
for r in range(38):
    rec = data[r*RECSZ: r*RECSZ+RECSZ]
    bsec = rec[AHEAD:AHEAD+BTER]
    for byte in bsec:
        modc[byte >> 4] += 1
for m in sorted(modc):
    print(f"  modifier {m:2d}: {modc[m]:6d}")

# C deploy: ASCII chars used (unit deployment)
print("\nC-section (deployment) ASCII char frequency (first 760 bytes of C):")
chc = Counter()
for r in range(38):
    rec = data[r*RECSZ: r*RECSZ+RECSZ]
    csec = rec[AHEAD+BTER:AHEAD+BTER+CDEP]
    for ch in csec:
        chc[ch] += 1
top = chc.most_common(40)
print("  total distinct chars:", len(chc))
for ch, n in top:
    name = chr(ch) if 0x20 <= ch < 0x7f else f"0x{ch:02x}"
    print(f"  {name!r:5}: {n}")
