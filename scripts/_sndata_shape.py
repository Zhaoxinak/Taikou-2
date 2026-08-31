#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P0 攻坚：把 833 条记录按 payload「结构指纹」聚类，识别可解码的字段族（word数组/byte数组/打包）。
目标：跳过填充类型(0x0c/0xf3)，对真实类型做语义初判。
"""
import struct
from collections import Counter, defaultdict

def read_records(path):
    d = open(path, 'rb').read()
    body = d[16:]
    return [body[i*49:(i+1)*49] for i in range(len(body)//49)]

recs = read_records('Taikou2 Original/SNDATA1.TR2')

# 每个记录：统计 payload(rec[6:49]) 里各字节出现次数，形成指纹
# 语义判断：
#  - word数组: 2字节对齐、值多为0x0c(12)或小值、无0xf3
#  - byte数组: 值域集中在某几个
#  - 填充: 0x0c/0xf3 占绝大多数
def shape(r):
    seg = r[6:49]
    c = Counter(seg)
    n = len(seg)
    f3 = c.get(0xf3,0); c0c = c.get(0x0c,0); zz = c.get(0x00,0)
    nonfill = n - f3 - c0c - zz
    # 检查是否 word 数组（2字节对齐小端）
    if nonfill >= 20:
        return 'data-heavy'
    if f3 >= 25:
        return 'f3-fill'
    if c0c >= 25:
        return '0c-fill'
    if f3+c0c+zz >= 38:
        return 'fill'
    return 'mixed'

# 按 type 聚合，看每 type 的 shape 一致性 + 记录数
bydict = defaultdict(list)
for r in recs:
    t = struct.unpack_from('<H', r, 0)[0] & 0xff
    bydict[t].append(r)

print(f"type 种类 {len(bydict)}")
# 列出非填充 type 中记录数>=3 的，给 shape + 样例 payload hex
print("\n=== 真实(非填充)类型，记录数>=3 ===")
for t in sorted(bydict):
    grp = bydict[t]
    if t in (0x0c, 0xf3): continue
    if len(grp) < 3: continue
    sh = Counter(shape(r) for r in grp)
    dom = sh.most_common(1)[0]
    r0 = grp[0]
    idw = struct.unpack_from('<H', r0, 0)[0]
    print(f"type=0x{t:02x} x{len(grp):3d}  shape={dom[0]:10s}({dom[1]}/{len(grp)})  idw=0x{idw:04x}  payload={r0[6:30].hex()}")
