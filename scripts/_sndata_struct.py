#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P0：分析 payload 结构。0x0c/0xf3 是高频结构字节。
目标：确定 payload 是否为「固定字段数组」，各字段偏移与语义。
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

import struct
from collections import Counter

def read_records(path):
    d = open(path, 'rb').read()
    body = d[16:]
    return [body[i*49:(i+1)*49] for i in range(len(body)//49)]

# 统计 payload (rec[6:49], 43B) 中每个字节位置的值分布
recs = read_records(_ROOT + '/Taikou2 Original/SNDATA1.TR2')
print(f"共 {len(recs)} 条。统计 rec[6:49] 43B 每位置值分布：")
# 找出 0x0c 与 0xf3 出现的位置模式
pos_0c = Counter(); pos_f3 = Counter()
for r in recs:
    for i in range(6, 49):
        b = r[i]
        if b == 0x0c: pos_0c[i-6] += 1
        elif b == 0xf3: pos_f3[i-6] += 1

print("\n0x0c 出现次数按 payload 偏移 (43B):")
print("  ", [(i, pos_0c[i]) for i in range(43) if pos_0c[i] >= 20])
print("\n0xf3 出现次数按 payload 偏移:")
print("  ", [(i, pos_f3[i]) for i in range(43) if pos_f3[i] >= 10])

# 非 0x0c/0xf3 的位置（真正承载数据的字段）
nonempty = Counter()
for r in recs:
    for i in range(6, 49):
        if r[i] not in (0x0c, 0xf3, 0x00):
            nonempty[i-6] += 1
print("\n非(0x0c/0xf3/0x00) 的「有效数据位」出现次数:")
print("  ", [(i, nonempty[i]) for i in range(43) if nonempty[i] > 0])
