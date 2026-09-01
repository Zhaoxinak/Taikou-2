#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P0 攻坚第一步：按 16B 头 + 49B stride 重读 SNDATA1/2.TR2，dump 每条记录。
用续159/164 的权威模型：rec[0]=id_word, rec[2]=sub_word, rec[4]=flag‖rel;
3 文本视图 = rec+6 (len43), rec+19 (len30), rec+32 (len17)，均为 GBK null 结尾。
目标：确认 payload 本质（文本 vs 二进制），并对各类型做初步文本归类。
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

import struct, json

def read_records(path):
    d = open(path, 'rb').read()
    # 16B 文件头 + N×49B 记录
    hdr = d[:16]
    body = d[16:]
    n = len(body) // 49
    recs = []
    for i in range(n):
        r = body[i*49:(i+1)*49]
        if len(r) < 49:
            break
        recs.append(r)
    return hdr, recs

def gbk(b):
    """GBK 解码到第一个 null 或非法序列，返回 (文本, 有效字节数)。"""
    if not b:
        return "", 0
    # 找第一个 null
    z = b.find(b'\x00')
    seg = b if z < 0 else b[:z]
    try:
        s = seg.decode('gbk', errors='strict')
        return s, len(seg)
    except:
        # 部分解码失败：逐字节找最长前缀
        for cut in range(len(seg), 0, -1):
            try:
                return seg[:cut].decode('gbk'), cut
            except:
                continue
        return "", 0

def classify(path):
    hdr, recs = read_records(path)
    print(f"### {path}  hdr={hdr.hex()}  记录数={len(recs)}")
    # type = id_word & 0xff (续154)
    from collections import Counter
    typecnt = Counter()
    for r in recs:
        idw = struct.unpack_from('<H', r, 0)[0]
        typecnt[idw & 0xff] += 1
    print(f"  type(id_word&0xff) 去重 {len(typecnt)} 种, TOP: {typecnt.most_common(15)}")
    return recs

for p in [_ROOT + '/Taikou2 Original/SNDATA1.TR2', _ROOT + '/Taikou2 Original/SNDATA2.TR2']:
    classify(p)
