#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_type_resource.py -- 静态 P0 命名语义初判（不依赖 emu 主循环）
读 scripts/sndata_emu_full_read.json（833 条记录的 id_word/sub_word/flag/type/payload），
对每 type 统计：
  - id_word 高字节（benum 候选 = id_word>>8）的取值范围
  - sub_word 取值范围
  - payload 首字节/长度/样本
并对照已知表规模（实体0..369 / 城0..199 / 国0..48 / 名称数千）给出「落点」初判。
输出 scripts/sndata_type_resource_hypothesis.json。
"""
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

import json, os
from collections import defaultdict

ROOT=_ROOT
data=json.load(open(os.path.join(ROOT,_ROOT + '/scripts/sndata_emu_full_read.json'),"r",encoding="utf-8"))
recs=data["records"]

def rng(xs):
    xs=[x for x in xs if x is not None]
    return (min(xs),max(xs),len(xs)) if xs else None

per_type=defaultdict(list)
for r in recs:
    per_type[r["type"]].append(r)

TABLES={"entity":(0,369),"castle":(0,199),"country":(0,48),"name":(0,4000)}

out={"by_type":{},"summary":[]}
for t in sorted(per_type, key=lambda x: x if isinstance(x,int) else int(x,16)):
    rs=per_type[t]
    hi=[ (r["id_word"]>>8) for r in rs ]
    sub=[ r["sub_word"] for r in rs ]
    fl=[ r["flag"] for r in rs ]
    hi_r=rng(hi); sub_r=rng(sub); fl_r=rng(fl)
    # 判断 benum 高字节落点
    hmin,hmax,_=hi_r
    land=[]
    for name,(lo,hi2) in TABLES.items():
        if hmin>=lo and hmax<=hi2:
            land.append(name)
    # payload 长度（payload_hex 固定 43B=86 hex chars）
    plen=set(len(r["payload_hex"])//2 for r in rs)
    sample=rs[0]
    info={
        "records":len(rs),
        "id_hi_byte": {"min":hmin,"max":hmax},
        "sub_word": {"min":sub_r[0],"max":sub_r[1]},
        "flag": {"min":fl_r[0],"max":fl_r[1]},
        "payload_len_bytes": sorted(plen),
        "landing_hypothesis": land if land else "unknown",
        "sample_id_word": sample["id_word"],
        "sample_sub_word": sample["sub_word"],
        "sample_payload_hex": sample["payload_hex"][:40],
    }
    out["by_type"][t]=info

# 汇总：按落点假设分组
from collections import Counter
grp=defaultdict(list)
for t,info in out["by_type"].items():
    key=tuple(sorted(info["landing_hypothesis"])) if info["landing_hypothesis"]!="unknown" else ("unknown",)
    grp[key].append(t)
out["summary"]=[{"landing":list(k),"types":v} for k,v in grp.items()]

with open(os.path.join(ROOT,_ROOT + '/scripts/sndata_type_resource_hypothesis.json'),"w",encoding="utf-8") as f:
    json.dump(out,f,ensure_ascii=False,indent=1)

# 打印 TOP
print(f"总类型数={len(per_type)}")
print("\n按 benum 高字节落点分组：")
for s in out["summary"]:
    print(f"  {s['landing']}: {len(s['types'])} 类型")
print("\n样例（前 25 类型）：")
for i,(t,info) in enumerate(sorted(out["by_type"].items(), key=lambda kv:-kv[1]["records"])):
    if i>=25: break
    print(f"  type={t} n={info['records']:>3} idHi=[{info['id_hi_byte']['min']:>3},{info['id_hi_byte']['max']:>3}] "
          f"sub=[{info['sub_word']['min']:>4},{info['sub_word']['max']:>4}] flag=[{info['flag']['min']:>4},{info['flag']['max']:>4}] -> {info['landing_hypothesis']}")
