# -*- coding: utf-8 -*-
"""按 file=id//2000, idx=id%2000 解码晋升消息 0x33d-0x343。"""
import os, re

HERE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(HERE, "_probe", "msgx", "all_messages.txt")

FILES = ["MESSAGE1.LZW", "MESSAGE2.LZW", "MESSAGE3.LZW", "MESSAGE4.LZW"]
# 按 file 分桶，存 idx->text
buckets = {f: {} for f in FILES}
for ln in open(p, encoding="utf-8"):
    m = re.match(r'^\[(\w+\.LZW)#(\d+)\] (.*)$', ln.rstrip("\n"))
    if m and m.group(1) in buckets:
        buckets[m.group(1)][int(m.group(2))] = m.group(3)

def by_id(mid):
    fi = mid // 2000
    idx = mid - fi * 2000
    if 0 <= fi < len(FILES):
        return buckets[FILES[fi]].get(idx)
    return None

out = ["=== 晋升事件消息 0x33d-0x343 ==="]
for mid in range(0x33d, 0x344):
    out.append(f"  0x{mid:04x}  {by_id(mid)!r}")
open(os.path.join(HERE, "_promo_msgs_fixed.txt"), "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out))
