# -*- coding: utf-8 -*-
"""解码 MESSAGE4.LZW（MSGX id 6000-7999，此前从未解码）。"""
import os, struct, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from real_assets import ls11_decompress

DATA_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "Taikou2 Original")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_probe", "msgx")
os.makedirs(OUT, exist_ok=True)

def decode_msgx(fname):
    raw = open(os.path.join(DATA_ROOT, fname), "rb").read()
    dec = ls11_decompress(raw)
    if not dec or dec[:4] != b"MSGX":
        return None, []
    n = struct.unpack_from("<H", dec, 4)[0]
    ptrs = [struct.unpack_from("<I", dec, 6 + i*4)[0] for i in range(n)]
    ptrs.append(len(dec))
    msgs = []
    for i in range(n):
        seg = dec[ptrs[i]:ptrs[i+1]]
        end = seg.find(b"\x00")
        if end >= 0: seg = seg[:end]
        try: txt = seg.decode("gbk", "replace")
        except Exception: txt = repr(seg)
        msgs.append(txt)
    return dec, msgs

for fn in ["MESSAGE1.LZW", "MESSAGE2.LZW", "MESSAGE3.LZW", "MESSAGE4.LZW"]:
    dec, msgs = decode_msgx(fn)
    if dec is None:
        print(f"{fn}: FAIL"); continue
    print(f"{fn}: raw={len(dec)}B  msgs={len(msgs)}")
    if fn == "MESSAGE4.LZW":
        with open(os.path.join(OUT, "all_messages4.txt"), "w", encoding="utf-8") as f:
            for i, t in enumerate(msgs):
                f.write(f"[MESSAGE4.LZW#{i}] (id=0x{6000+i:04x}) {t}\n")
        json_path = os.path.join(OUT, "message4.json")
        import json
        json.dump({"file": fn, "id_base": 6000, "count": len(msgs),
                   "messages": msgs}, open(json_path, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"  -> {OUT}/all_messages4.txt  +  message4.json")
