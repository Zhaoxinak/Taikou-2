# -*- coding: utf-8 -*-
import json
from collections import Counter

texts = json.load(open("scripts/msgx_all_texts.json", "r", encoding="utf-8"))["texts"]
lines = []
lines.append("=== MSGX personality bank 0x1162..0x1169 ===")
for i in range(8):
    k = 0x1162 + i
    lines.append(f"  type{i} msg {k:#x}: {texts[str(k)]}")
lines.append(f"  lead-in 0x1161: {texts[str(0x1161)]}")

bs = open("Taikou2 Original/BSDATA1.TR2", "rb").read()
STRIDE, N = 59, 700

def name(i):
    r = bs[i * STRIDE:(i + 1) * STRIDE]
    s = r[0:7].split(b"\x00")[0].decode("gbk", "replace")
    g = r[7:14].split(b"\x00")[0].decode("gbk", "replace")
    return s + g

pers = Counter()
famous = []
for i in range(N):
    r = bs[i * STRIDE:(i + 1) * STRIDE]
    if name(i).startswith("姓"):
        continue
    v = r[0x28]
    p = v & 7
    pers[p] += 1
    nm = name(i)
    if any(x in nm for x in ["信长", "秀吉", "家康", "信玄", "谦信", "政宗", "元就", "利家", "光秀", "胜家", "胜赖", "秀忠"]):
        famous.append(f"  {nm}: +0x1c={v:#04x} pers={p} flags={v & ~7:#04x} 1f={r[0x2b]} stam={r[0x2c]}")

lines.append("=== personality (&7) distribution ===")
lines.append(str(pers.most_common()))
lines.append("=== famous ===")
lines.extend(famous)

# table 0x50bf48 = 国 map?
mem = open("scripts/_unpacked_mem.bin", "rb").read()
raw = mem[0x50bf48 - 0x400000:0x50bf48 - 0x400000 + 63]
lines.append("=== 0x50bf48[0..62] (→0..48) ===")
lines.append(str(list(raw)))

# Is +0x1f a face id? Check if sorted/grouped by clan
lines.append("=== +0x1f vs surname clusters (top surnames) ===")
from collections import defaultdict
by_sur = defaultdict(list)
for i in range(N):
    r = bs[i * STRIDE:(i + 1) * STRIDE]
    sur = r[0:7].split(b"\x00")[0].decode("gbk", "replace")
    if sur.startswith("姓") or not sur:
        continue
    by_sur[sur].append(r[0x2b])
for sur, idxs in sorted(by_sur.items(), key=lambda x: -len(x[1]))[:15]:
    lines.append(f"  {sur}: n={len(idxs)} 1f={sorted(set(idxs))} ")

# Check GAME: 63 = face count?
# Search for cmp 0x3f or 63 near face loading
lines.append("=== done ===")
open("scripts/_scratch/_pers_1f.txt", "w", encoding="utf-8").write("\n".join(lines))
print("\n".join(lines))
