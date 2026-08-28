#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""经验式解析 SNDATA 原始字节, 找记录边界."""
import struct, sys
sd1 = open(r"F:/Games/Taikou2/SNDATA1.TR2","rb").read()
sd2 = open(r"F:/Games/Taikou2/SNDATA2.TR2","rb").read()
print(f"SNDATA1 size={len(sd1)}  SNDATA2 size={len(sd2)}  identical={sd1==sd2}")
sig = b"TAIKOU2_SCENARIO"
assert sd1[:len(sig)] == sig, "no sig"
# 16 字节签名后... 实际签名是?
print("bytes[0:18] hex:", sd1[:18].hex())
# signature 可能带长度: 看 [0:16] 是 TAIKOU2_SCENARIO, [16]='K'(0x4b)?
# 试: 签名 = [0:16], 数据从16开始
off = 16
def u16(b,o): return struct.unpack("<H", b[o:o+2])[0]
def u32(b,o): return struct.unpack("<I", b[o:o+4])[0]
h0 = u16(sd1, off); h1 = u16(sd1, off+2)
print(f"@16 u16 h0={h0} (0x{h0:x})  @18 u16 h1={h1} (0x{h1:x})")
# 打印 [16:96] 的逐字节, 便于找结构
print("hex[16:96]:", sd1[16:96].hex())
print("ascii[16:96]:", "".join(chr(c) if 32<=c<127 else '.' for c in sd1[16:96]))
# 试不同签名长度 (15/16/17/20) 看哪种使后续成结构
for siglen in (15,16,17,20):
    print(f"\nsiglen={siglen}: next u16 = {u16(sd1,siglen)} (0x{u16(sd1,siglen):x}), u32={u32(sd1,siglen)}")
# 文件整体结构: 试把 (40856 - 16) 按若干候选 stride 切
rem = len(sd1) - 16
print(f"\nremaining after 16-byte sig = {rem}")
for stride in [0x2bc, 0x2bd, 0x100, 0x200, 0x300, 0x400, 0x500, 0x1000, 700, 1400, 2800]:
    if rem % stride == 0:
        print(f"  rem % {stride:#x} == 0 -> {rem//stride} records")
# 找文件中出现频率高的 2 字节对齐常量 (疑似记录分隔/计数)
from collections import Counter
c = Counter(sd1[i:i+2] for i in range(16, len(sd1)-1, 2))
print("\ntop 2-byte little-endian values:", [(v.hex(), n) for v,n in c.most_common(10)])
# 找 ASCII 字符串片段
import re
strs = [m.group().decode('latin1') for m in re.finditer(rb"[ -~]{5,}", sd1)]
print(f"\nASCII strings in SNDATA1 ({len(strs)}):")
for s in strs[:40]:
    print("  ", s)
print("DONE")
