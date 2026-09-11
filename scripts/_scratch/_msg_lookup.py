#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.chdir(r"F:\Games\Taikou 2")
out = open("scripts/_scratch/_msg_lookup.txt", "w", encoding="utf-8")

for fn in ["scripts/msgx_all_texts.json", "scripts/msgx_id_map.json", "scripts/msgx_text_tables.json"]:
    d = json.load(open(fn, encoding="utf-8"))
    out.write(f"==== {fn} {type(d).__name__}\n")
    if isinstance(d, dict):
        out.write(f"keys={list(d.keys())[:12]}\n")
        for k, v in list(d.items())[:5]:
            out.write(f"  {k}: {type(v).__name__} {str(v)[:100]}\n")
    else:
        out.write(f"len={len(d)}\n")

# Try id map
m = json.load(open("scripts/msgx_id_map.json", encoding="utf-8"))
ids = [0xDB2, 0xDB3, 0xDB4, 0xDB5, 0xDBE, 0xDBF, 0xDC0, 0xDC2, 0xDC3, 0x16E8, 0x16DF, 0x1B76]


def lookup(d, i):
    cands = [i, str(i), hex(i), f"{i:x}", f"0x{i:x}", f"{i:04X}", f"{i:04x}"]
    if isinstance(d, dict):
        for c in cands:
            if c in d:
                return d[c]
        # nested texts
        for k in ("texts", "messages", "by_id", "map", "entries", "files"):
            if k in d and isinstance(d[k], dict):
                for c in cands:
                    if c in d[k]:
                        return d[k][c]
            if k in d and isinstance(d[k], list) and isinstance(i, int) and i < len(d[k]):
                return d[k][i]
    if isinstance(d, list) and i < len(d):
        return d[i]
    return None


for fn in ["scripts/msgx_id_map.json", "scripts/msgx_all_texts.json", "scripts/msgx_text_tables.json", "scripts/hexmes_msgs.json"]:
    d = json.load(open(fn, encoding="utf-8"))
    out.write(f"\n-- lookups in {fn} --\n")
    for i in ids:
        v = lookup(d, i)
        if v is None and isinstance(d, dict) and "files" in d:
            # deep search
            found = None
            stack = [d]
            while stack and found is None:
                cur = stack.pop()
                if isinstance(cur, dict):
                    for c in (i, str(i), hex(i)):
                        if c in cur:
                            found = cur[c]
                            break
                    stack.extend(cur.values())
                elif isinstance(cur, list):
                    stack.extend(cur[:50])
            v = found
        out.write(f"  {i:#x}={i}: {str(v)[:120] if v is not None else None}\n")

out.close()
print("ok")
