# -*- coding: utf-8 -*-
"""在已解码消息中找晋升/官位相关台词，输出 id 与文本。"""
import os, re

HERE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(HERE, "_probe", "msgx", "all_messages.txt")

ranks = ["浪人", "步兵头", "队长", "侍大将", "部将", "家老", "宿老", "大名", "城主"]
kw = ["出世", "栄進", "栄進", "官位", "任官", "推挙", "推薦", "任命", "昇進", "昇格",
      "取り立て", "取りたて", "取り立", "出世", "官途", "位", "格式"]

lines = open(path, encoding="utf-8").read().splitlines()
hits = []
for ln in lines:
    # [FILE.LZW#NUM] (id=0xXXXX) text
    m = re.match(r'^\[(\w+\.LZW)#(\d+)\] \(id=0x([0-9a-f]+)\) (.*)$', ln)
    if not m:
        continue
    fid = int(m.group(3), 16)
    txt = m.group(4)
    if any(rk in txt for rk in ranks):
        hits.append((fid, txt))
    elif any(k in txt for k in kw):
        hits.append((fid, txt))

hits = sorted(set(hits))
out = [f"匹配 {len(hits)} 条\n"]
for fid, txt in hits:
    out.append(f"  0x{fid:04x}  {txt}")
open(os.path.join(HERE, "_promo_msgs.txt"), "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out[:80]))
