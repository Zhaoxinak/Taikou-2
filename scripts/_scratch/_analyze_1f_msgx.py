# -*- coding: utf-8 -*-
import json

texts = json.load(open("scripts/msgx_all_texts.json", "r", encoding="utf-8"))["texts"]
out = []
base = 0x1162
for i in range(8):
    k = str(base + i)
    out.append(f"{base + i:#x}\t{texts.get(k, 'MISSING')}")
out.append(f"0x1161\t{texts.get(str(0x1161), 'MISSING')}")
for i in range(4445, 4460):
    out.append(f"dec{i}\t{texts.get(str(i), 'MISSING')}")

mem = open("scripts/_unpacked_mem.bin", "rb").read()
BASE = 0x400000
tbl = 0x50bf48
raw = mem[tbl - BASE: tbl - BASE + 128]
out.append("table 0x50bf48 first 64: " + " ".join(f"{b:02x}" for b in raw[:64]))
vals = list(raw[:63])
out.append(f"vals0..62 = {vals}")
out.append(f"min={min(vals)} max={max(vals)} unique={len(set(vals))}")

bs = open("Taikou2 Original/BSDATA1.TR2", "rb").read()
STRIDE, N = 59, 700
match = tot = 0
samples = []
for i in range(N):
    r = bs[i * STRIDE:(i + 1) * STRIDE]
    sur = r[0:7].split(b"\x00")[0].decode("gbk", "replace")
    if sur.startswith("姓"):
        continue
    idx = r[0x2b]
    city = r[0x31]
    mapped = raw[idx]
    tot += 1
    if mapped == city:
        match += 1
    if len(samples) < 25:
        giv = r[7:14].split(b"\x00")[0].decode("gbk", "replace")
        samples.append(f"{sur}{giv}: 1f={idx} map={mapped} city={city} prov={r[0x30]}")
out.append(f"1f->table == city: {match}/{tot}")
matchp = sum(
    1
    for i in range(N)
    if not bs[i * STRIDE:i * STRIDE + 2].decode("latin1", "replace").startswith("姓")
    and raw[bs[i * STRIDE + 0x2b]] == bs[i * STRIDE + 0x30]
)
# better matchp
mp = 0
tn = 0
for i in range(N):
    r = bs[i * STRIDE:(i + 1) * STRIDE]
    sur = r[0:7].split(b"\x00")[0].decode("gbk", "replace")
    if sur.startswith("姓"):
        continue
    tn += 1
    if raw[r[0x2b]] == r[0x30]:
        mp += 1
out.append(f"1f->table == prov: {mp}/{tn}")
out.extend(samples)

# Also: is 0x50bf48 a province->city capital table? size 49?
out.append("prov capitals? table[0..48]: " + str(list(raw[:49])))
# known: many games store 国→本城
# check uniqueness of table[0..48]
out.append(f"unique in 0..48: {len(set(raw[:49]))}")

# Cross: MSGX for +0x1c - also search texts mentioning 足轻/骑马 etc for troop types
for kw in ["足轻", "骑士", "铁炮", "弓", "骑马", "兵种", "枪", "骑兵", "水军"]:
    hits = [(k, v) for k, v in texts.items() if kw in v]
    if hits:
        out.append(f"MSGX '{kw}' count={len(hits)} e.g. {hits[0][0]}:{hits[0][1][:60]}")

open("scripts/_scratch/_1f_table.txt", "w", encoding="utf-8").write("\n".join(out))
print("OK", len(out))
for line in out[:30]:
    print(line)
