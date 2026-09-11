# -*- coding: utf-8 -*-
import importlib.util
spec = importlib.util.spec_from_file_location("pn", "scripts/province_names_ref.py")
# just inline the names
PROVINCE_NAMES = None
# read from the file by exec the list
ns = {}
code = open("scripts/province_names_ref.py", encoding="utf-8").read()
# extract PROVINCE_NAMES by running safe portion
exec([l for l in code.splitlines() if l.startswith("PROVINCE_NAMES") or (PROVINCE_NAMES is None and "PROVINCE_NAMES" in dir()) or True][0] if False else code.split("def load")[0], ns)
PROVINCE_NAMES = ns["PROVINCE_NAMES"]
mem = open("scripts/_unpacked_mem.bin", "rb").read()
raw = mem[0x50bf48 - 0x400000:0x50bf48 - 0x400000 + 63]
bs = open("Taikou2 Original/BSDATA1.TR2", "rb").read()
STRIDE = 59

def name(i):
    r = bs[i * STRIDE:(i + 1) * STRIDE]
    s = r[0:7].split(b"\x00")[0].decode("gbk", "replace")
    g = r[7:14].split(b"\x00")[0].decode("gbk", "replace")
    return s + g

lines = []
for i, label in [(13, "织田信长"), (19, "前田利家"), (199, "武田信玄"), (257, "上杉谦信"),
                 (304, "德川家康"), (112, "明智光秀"), (500, "毛利元就"), (1, "柴田胜家"),
                 (364, "伊达?"), (100, "伊达辉宗")]:
    r = bs[i * STRIDE:(i + 1) * STRIDE]
    idx = r[0x2b]
    prov = raw[idx]
    lines.append(f"{name(i)}: 1f={idx} -> 国[{prov}]={PROVINCE_NAMES[prov]}  city={r[0x31]} prov_field={r[0x30]}={PROVINCE_NAMES[r[0x30]] if r[0x30]<49 else 'N/A'}")

# clan home check
lines.append("\n=== clan 1f geography ===")
clans = {}
for i in range(700):
    r = bs[i * STRIDE:(i + 1) * STRIDE]
    sur = r[0:7].split(b"\x00")[0].decode("gbk", "replace")
    if sur.startswith("姓"):
        continue
    idx = r[0x2b]
    prov = raw[idx]
    clans.setdefault(sur, []).append((idx, prov, PROVINCE_NAMES[prov]))
for sur in ["织田", "武田", "德川", "上杉", "毛利", "岛津", "北条", "伊达", "朝仓", "三好", "真田"]:
    if sur in clans:
        u = sorted(set((a, b, c) for a, b, c in clans[sur]))
        lines.append(f"{sur}: {u}")

open("scripts/_scratch/_1f_geo.txt", "w", encoding="utf-8").write("\n".join(lines))
print("\n".join(lines))
