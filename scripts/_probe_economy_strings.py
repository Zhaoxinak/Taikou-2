#!/usr/bin/env python3
# Recon: scan unpacked Taikou2 EXE for economy/trade-related GBK strings.
# Usage: python _probe_economy_strings.py [keyword1 keyword2 ...]
import sys, re, json

BIN = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000

data = open(BIN, "rb").read()
print(f"image size = {len(data)} ({len(data)//1024} KB), VA base 0x{BASE:x}", flush=True)

# Decode all GBK printable runs (>=2 chars) with file offset + VA.
# A run = sequence of (ASCII 0x20-0x7e) or (GBK lead 0x81-0xfe + trail 0x40-0xfe)
pat = re.compile(rb'(?:[\x20-\x7e]|[\x81-\xfe][\x40-\xfe]){2,}', re.DOTALL)

results = []
for m in pat.finditer(data):
    s = m.group(0)
    try:
        txt = s.decode('gbk')
    except Exception:
        continue
    off = m.start()
    va = BASE + off
    results.append((off, va, txt))

print(f"total GBK runs decoded: {len(results)}", flush=True)

# Build a searchable index file (once) for reuse.
idx_path = "F:/Games/Taikou 2/scripts/_string_index.json"
if len(sys.argv) <= 1:
    # Default: dump index and run built-in keyword scan.
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump([[o, v, t] for (o, v, t) in results], f, ensure_ascii=False)
    print(f"wrote index -> {idx_path} ({len(results)} entries)", flush=True)

# Keyword scan
default_kw = ["買","売","値","相場","価","商","米","木","鉄","砲","馬","船","茶","絹","薬","書","砂","金","刀","塩","油","魚","綿","麻","鉄炮","值段","买卖","交易所","市"]
# allow rune-level substring search
kw = sys.argv[1:] if len(sys.argv) > 1 else default_kw

hits = {}
for o, v, t in results:
    for k in kw:
        if k in t:
            hits.setdefault(k, []).append((v, t))
            break

for k in kw:
    lst = hits.get(k, [])
    if not lst:
        continue
    print(f"\n=== keyword '{k}' : {len(lst)} hits ===")
    for v, t in lst[:40]:
        print(f"  0x{v:06x}  {t}")
