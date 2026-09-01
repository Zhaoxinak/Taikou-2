#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_s1_unify_probe.py -- 探针：解密 SNDATA，抽 S1 370×59B，与 BSDATA 700×59B 对齐比对。"""
import os, struct, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(ROOT, "Taikou2 Original")

def load(n):
    return open(os.path.join(ORIG, n), "rb").read()

def decrypt(raw):
    key = raw[0x12] ^ raw[0x13]
    return key, bytes(b ^ key for b in raw)

def gbk7(b):
    b = b.split(b"\x00")[0]
    if not b:
        return None
    try:
        return b.decode("gbk")
    except Exception:
        return None

for scen in (1, 2):
    raw = load("SNDATA%d.TR2" % scen)
    key, dec = decrypt(raw)
    print("=== SNDATA%d  len=%d  key=0x%02x ===" % (scen, len(raw), key))
    for sbase in (0x58c, 0x598):
        s1 = sbase + 22
        ok = 0
        names = []
        for i in range(370):
            r = dec[s1 + i * 59: s1 + i * 59 + 59]
            sur, giv = gbk7(r[0:7]), gbk7(r[7:14])
            if sur is not None and giv is not None:
                ok += 1
            names.append((sur, giv))
        print("  stream_base=0x%03x  S1@0x%04x  GBK双段可解=%d/370  前5=%s"
              % (sbase, s1, ok, names[:5]))

# BSDATA 参照
bs = load("BSDATA1.TR2")
print("=== BSDATA1 len=%d 前3条姓名 ===" % len(bs))
for i in range(3):
    r = bs[i * 59:(i + 1) * 59]
    print("  #%d %s %s  w0e=%04x w10=%04x w12=%04x w14=%04x w36=%04x"
          % (i, gbk7(r[0:7]), gbk7(r[7:14]),
             *struct.unpack_from("<H", r, 0x0e), *struct.unpack_from("<H", r, 0x10),
             *struct.unpack_from("<H", r, 0x12), *struct.unpack_from("<H", r, 0x14),
             *struct.unpack_from("<H", r, 0x36)))

# BSDATA 中 0x0e / 0x12 两个「被解码器丢弃」字段的分布
for off in (0x0e, 0x12):
    c = collections.Counter(struct.unpack_from("<H", bs, i * 59 + off)[0] for i in range(700))
    print("  BSDATA1 w@0x%02x distinct=%d top5=%s" % (off, len(c), c.most_common(5)))
