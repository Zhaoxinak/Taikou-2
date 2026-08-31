# -*- coding: utf-8 -*-
"""按函数名/关键词检索 msgx_id_map.json 的 sites，用于给 bitset 消费者定名。"""
import json, os, sys, re

HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "msgx_id_map.json"), encoding="utf-8"))
SITES = d["sites"]
T = json.load(open(os.path.join(HERE, "msgx_all_texts.json"), encoding="utf-8"))["texts"]

def hx(v):
    return v if isinstance(v, int) else int(v, 16)


BYFUNC = {}
for s in SITES:
    s = dict(s)
    s["func"] = "0x%06x" % hx(s["func"])
    s["at"] = hx(s["at"])
    s["callee"] = s["callee"] if isinstance(s["callee"], str) else "0x%06x" % s["callee"]
    BYFUNC.setdefault(s["func"], []).append(s)


def txt(i):
    for k in (str(i), "0x%x" % i):
        if k in T:
            return T[k]
    return "?"


def show_func(f, limit=40):
    f = f.lower()
    if not f.startswith("0x"):
        f = "0x" + f
    ss = BYFUNC.get(f, [])
    print(f"--- {f}  ({len(ss)} 条消息)")
    for s in ss[:limit]:
        ids = []
        for i in s["ids"]:
            try:
                ids.append("0x%x" % i)
            except TypeError:
                ids.append(str(i))
        print("    @0x%06x -> %s  ids=%s" % (s['at'], s['callee'], ids))
        for i in s["ids"]:
            if isinstance(i, int):
                print("        0x%x [%d] %s" % (i, i, txt(i)))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "kw":
        kws = sys.argv[2:]
        seen = set()
        for s in SITES:
            allt = " ".join(txt(i) for i in s["ids"])
            if any(k in allt for k in kws):
                key = "0x%06x" % hx(s["func"])
                if key in seen:
                    continue
                seen.add(key)
                print("\n### func %s" % s["func"])
            if s["func"] in seen and any(k in allt for k in kws):
                print("    @0x%06x" % hx(s["at"]))
                for i in s["ids"]:
                    print("        0x%x %s" % (i, txt(i)))
    else:
        for f in sys.argv[1:]:
            show_func(f)
