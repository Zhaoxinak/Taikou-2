#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""提取 SNDATA1/2 全部 833 条 49B 记录：类型头 + 43B payload + 分类。
输出 scripts/sndata_records.json（供复刻增量映射字段）。"""
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>

import os, json
from collections import Counter

DATA = r"F:\Games\Taikou2"
OUT = _ROOT + '/scripts/sndata_records.json'
N, SZ = 833, 49
FILLER = {0x00,0x01,0x0c,0x0d,0x0e,0x0f,0xf3,0xff}

def parse(path):
    raw = open(path, "rb").read()
    assert raw[:16] == b"TAIKOU2_SCENARIO", raw[:16]
    body = raw[16:]
    recs = [body[i*SZ:(i+1)*SZ] for i in range(N)]
    out = []
    for i, r in enumerate(recs):
        idw = r[0] | (r[1]<<8)
        sub = r[4] | (r[5]<<8)
        flag = r[6]
        rel = r[12] | (r[13]<<8)
        payload = r[6:49]  # 43-byte entity struct (loader copies to 0x522c88)
        real = [b for b in r if b not in FILLER]
        # 类型签名 = 非填充字节在记录中的分布指纹
        cls = ("empty" if not real else
               "flagblock" if all(b in {0x01,0x00} for b in real) else
               "datablock")
        out.append({
            "idx": i,
            "id_word": idw,
            "sub_word": sub,
            "flag": flag,
            "rel_word": rel,
            "class": cls,
            "real_byte_count": len(real),
            "payload_hex": payload.hex(),
        })
    return out

res = {}
for sc, fn in [("scenario1","SNDATA1.TR2"), ("scenario2","SNDATA2.TR2")]:
    recs = parse(os.path.join(DATA, fn))
    cls_cnt = Counter(r["class"] for r in recs)
    idw_cnt = Counter(r["id_word"] for r in recs)
    res[sc] = {
        "count": len(recs),
        "class_counts": dict(cls_cnt),
        "id_word_counts": {f"0x{v:04x}": n for v,n in idw_cnt.most_common(15)},
        "records": recs,
    }

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print(f"OK -> {OUT}")
for sc in res:
    print(f"  {sc}: {res[sc]['count']} 条, 分类={res[sc]['class_counts']}")
    print(f"    id_word top: {list(res[sc]['id_word_counts'].items())[:6]}")
