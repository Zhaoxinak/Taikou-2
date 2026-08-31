import json
res=json.load(open("scripts/castle_values.json"))
def show(c):
    print(f" id={c['id']:3d} off={c['officer_idx']:4d} par={c['parent_castle']:3d} "
          f"b08={c['b08']:3d} b09={c['b09']:3d} w0a={c['w0a']:5d} b0c={c['b0c']:3d} b0d={c['b0d']:3d} "
          f"b0e={c['b0e']:3d} b0f={c['b0f']:3d} w10={c['w10']:5d} w12={c['w12']:5d} w14={c['w14']:6d} "
          f"w16={c['w16']:4d} w18={c['w18']:5d} b1a={c['b1a']:3d} w1b={c['w1b']:5d} w1d={c['w1d']:5d} type={c['type']}")
print("=== scenario1 castles 0..19 (all fields) ===")
for c in res["scenario1"][:20]:
    show(c)
# which byte/word field is in range 0..48 (province candidate)?
import collections
for fld in ("b08","b09","b0c","b0d","b0e","b0f","b1a","w10","w12","w14","w16","w18","w1b","w1d","parent_castle","officer_idx"):
    vals=[c[fld] for c in res["scenario1"]]
    in48=sum(1 for v in vals if 0<=v<=48)
    in369=sum(1 for v in vals if 0<=v<=369)
    print(f"  {fld:14s} min={min(vals):6d} max={max(vals):6d}  in0..48={in48:3d}  in0..369={in369:3d}")
