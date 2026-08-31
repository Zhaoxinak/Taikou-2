# -*- coding: utf-8 -*-
import json, glob

s = open("F:/Games/Taikou 2/BREAKTHROUGHS.md", encoding="utf-8").read()
i = s.find("续131）")
j = s.find("续130）")
blk = s[i:j]
print("续131 block len:", len(blk))
TOK = ["0x49a5c0", "0x49a5e0", "0x5d2", "0x618", "0x619", "0x2e", "1490", "1560",
       "0x5205F0", "+0x1b", "220/220", "21/21", "1493..1582", "0x49a400",
       "0x5d2 仅 1 处", "bsdata_lifespan_ref.py", "续43", "续59", "32*A + B",
       "255 哨兵", "71 个", "64 个", "0x7F"]
miss = [t for t in TOK if t not in blk]
for t in TOK:
    print(("  OK   " if t in blk else "  MISS "), t)
print("\nMISSING:", miss if miss else "无")

print("\n=== 全 spec JSON 有效性 ===")
bad = 0
for p in sorted(glob.glob("F:/Games/Taikou 2/scripts/*_spec.json")):
    try:
        json.load(open(p, encoding="utf-8"))
    except Exception as e:
        print("  BAD", p, e)
        bad += 1
print("  全部有效" if bad == 0 else f"  {bad} 个损坏")

d = json.load(open("F:/Games/Taikou 2/scripts/bsdata_spec.json", encoding="utf-8"))
print("\n=== bsdata_spec ===")
print("  birth_age_encoding.status:", d["birth_age_encoding"]["status"])
print("  refuted:", list(d["refuted_hypotheses_131"].keys()))
print("  reference_impl:", d["reference_impl"])
print("  still_unknown 已闭:", sum(1 for x in d["still_unknown"] if x.startswith("✅")),
      "/", len(d["still_unknown"]))
