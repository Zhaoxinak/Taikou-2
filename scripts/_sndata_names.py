#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续176：从 SNDATA 记录 payload 提取嵌入 GBK 名，交叉对照城/武将名表，定记录语义。
方法：对每条记录的 payload，按 0x0c/0x23/0x4c/0xf3 等结构字节分割，取可 GBK 解码的
≥2 字节段；去掉噪声后，统计高频名称片段。
"""
import struct, json
from collections import Counter, defaultdict

def read_records(path):
    d = open(path, 'rb').read()
    body = d[16:]
    return [body[i*49:(i+1)*49] for i in range(len(body)//49)]

def gbk(b):
    try: return b.decode('gbk')
    except: return None

def extract_names(r):
    """返回 payload 里所有可 GBK 解码的 ≥2 字节名段（去掉含0x0c/0xf3的）。"""
    seg = r[6:49]
    out = []
    # 逐字节扫描，累积连续非结构字节段
    cur = bytearray()
    def flush():
        nonlocal cur
        if len(cur) >= 2:
            t = gbk(bytes(cur))
            if t and sum(1 for c in t if 0x4e00 <= ord(c) <= 0x9fff) >= 1:
                out.append(t)
        cur = bytearray()
    for b in seg:
        if b in (0x0c, 0xf3, 0x00, 0x01, 0x05, 0x07, 0x0d, 0x23, 0x4c):
            flush()
        else:
            cur.append(b)
    flush()
    return out

recs = read_records('Taikou2 Original/SNDATA1.TR2')
# 提取所有名称
name_counter = Counter()
bytype_names = defaultdict(list)
for r in recs:
    t = struct.unpack_from('<H', r, 0)[0] & 0xff
    names = extract_names(r)
    bytype_names[t].append(names)
    for n in names:
        name_counter[n] += 1

print(f'总提取名称片段 {len(name_counter)} 个不同值')
print('\n=== 最高频名称片段 TOP 40 ===')
for n, c in name_counter.most_common(40):
    print(f'  {n!r}  x{c}')
