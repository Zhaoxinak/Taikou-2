#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P0：在全部 833 条记录中，找「3 文本视图」里有真实可读 GBK 文本的样本。
若几乎没有 → 续165 的「3 文本列」理论对多数类型不成立，payload 是二进制字段。
若有 → 列出类型与其文本，直接给命名/描述。
"""
import struct

def read_records(path):
    d = open(path, 'rb').read()
    body = d[16:]
    return [body[i*49:(i+1)*49] for i in range(len(body)//49)]

def readable(seg):
    """返回 (最长连续 GBK 可读子串, 长度)。要求不含 0x0c/0xf3/0x00 等结构字节。"""
    z = seg.find(b'\x00')
    s = seg if z < 0 else seg[:z]
    # 去除 0x0c(12)/0xf3(243) 高频结构字节
    clean = bytes(b for b in s if b not in (0x0c, 0xf3, 0x01, 0x05, 0x07, 0x0d))
    if not clean:
        return "", 0
    try:
        t = clean.decode('gbk')
        return t, len(clean)
    except:
        best = ("", 0)
        for i in range(len(clean)):
            for j in range(i+2, min(i+40, len(clean))+1):
                try:
                    sub = clean[i:j].decode('gbk')
                    if len(sub) > best[1]:
                        best = (sub, len(sub))
                except: break
        return best

def scan(path):
    recs = read_records(path)
    found = []
    for r in recs:
        idw, subw, flagrel = struct.unpack_from('<HHH', r, 0)
        for off, label in [(6,'v6'),(19,'v19'),(32,'v32')]:
            t, ln = readable(r[off:49])
            # 要求至少 4 个纯可读字符
            if ln >= 4 and all(0x20 <= ord(c) < 0x7f or 0x4e00 <= ord(c) <= 0x9fff for c in t):
                found.append((idw, off, label, t))
    return found

for p in ['Taikou2 Original/SNDATA1.TR2', 'Taikou2 Original/SNDATA2.TR2']:
    f = scan(p)
    print(f"### {p}  有真实可读文本的记录视图: {len(f)} 条")
    for idw, off, label, t in f[:40]:
        print(f"  idw=0x{idw:04x} {label}@{off}: {t!r}")
