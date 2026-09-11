#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, struct
sys.path.insert(0, r"F:\Games\Taikou 2\scripts")
from real_assets import ls11_decompress

ROOT = r"F:\Games\Taikou 2"
ORIG = os.path.join(ROOT, "Taikou2 Original")
HERE = os.path.join(ROOT, "scripts")
OUT = os.path.join(HERE, "_scratch", "_gaiji_msg_hits.txt")

GAIJI = {c: bytes([(c >> 8) & 0xFF, c & 0xFF]) for c in range(0xA140, 0xA150)}

def try_gbk_around(data, i, radius=40):
    """Extract nearby bytes and try decode with gaiji marked."""
    a = max(0, i - radius)
    b = min(len(data), i + 2 + radius)
    chunk = data[a:b]
    # walk and decode: if gaiji, mark as [A1xx]
    out = []
    j = 0
    while j < len(chunk):
        if j + 1 < len(chunk):
            code = (chunk[j] << 8) | chunk[j + 1]
            if 0xA140 <= code <= 0xA14F:
                out.append("[%04X]" % code)
                j += 2
                continue
            # GBK lead?
            if 0x81 <= chunk[j] <= 0xFE and 0x40 <= chunk[j + 1] <= 0xFE:
                try:
                    out.append(bytes([chunk[j], chunk[j + 1]]).decode("gbk"))
                    j += 2
                    continue
                except Exception:
                    pass
        # ascii / control
        if 32 <= chunk[j] < 127:
            out.append(chr(chunk[j]))
        elif chunk[j] == 0:
            out.append("|")
        else:
            out.append("<%02X>" % chunk[j])
        j += 1
    return "".join(out)

lines = []
for fn in ["MESSAGE1.LZW", "MESSAGE2.LZW", "MESSAGE3.LZW", "MESSAGE4.LZW", "HEXMES.LZW"]:
    raw = open(os.path.join(ORIG, fn), "rb").read()
    dec = ls11_decompress(raw)
    lines.append("===== %s raw=%d dec=%d =====" % (fn, len(raw), len(dec)))
    for c, pat in GAIJI.items():
        start = 0
        while True:
            i = dec.find(pat, start)
            if i < 0:
                break
            ctx = try_gbk_around(dec, i, 50)
            lines.append("  %s @%d code=%04X ctx=%s" % (fn, i, c, ctx))
            start = i + 1

# Also scan name tables in MEM @0x521aa8 / 0x520660
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
for name, va, n, stride in [("surname", 0x521aa8, 1000, 7), ("given", 0x520660, 1000, 7)]:
    lines.append("===== MEM %s @%X =====" % (name, va))
    off = va - BASE
    for i in range(n):
        slot = MEM[off + i * stride: off + i * stride + stride]
        s = slot.split(b"\x00")[0]
        codes = []
        for k in range(0, len(s) - 1, 2):
            codes.append((s[k] << 8) | s[k + 1])
        hit = [c for c in codes if 0xA140 <= c <= 0xA14F]
        if hit:
            ctx = try_gbk_around(s + b"\x00", 0, 20)
            lines.append("  id=%d codes=%s raw=%s decoded_try=%s" % (
                i, [hex(c) for c in codes], s.hex(), ctx))

# Scan full MEM for GBK string-like sequences containing gaiji
# (look for pattern: printable GBK or gaiji, length >= 2 chars, null terminated)
lines.append("===== MEM string scan (null-terminated with gaiji) =====")
found = 0
i = 0
while i < len(MEM) - 4:
    # look for A1 4x
    if MEM[i] == 0xA1 and 0x40 <= MEM[i + 1] <= 0x4F:
        # expand left/right as GBK string
        L = i
        while L >= 2:
            b0, b1 = MEM[L - 2], MEM[L - 1]
            code = (b0 << 8) | b1
            if 0xA140 <= code <= 0xA14F or (0x81 <= b0 <= 0xFE and 0x40 <= b1 <= 0xFE and b1 != 0x7F):
                L -= 2
            else:
                break
        R = i + 2
        while R + 1 < len(MEM):
            b0, b1 = MEM[R], MEM[R + 1]
            code = (b0 << 8) | b1
            if 0xA140 <= code <= 0xA14F or (0x81 <= b0 <= 0xFE and 0x40 <= b1 <= 0xFE and b1 != 0x7F):
                R += 2
            elif 32 <= b0 < 127:
                R += 1
            else:
                break
        # require nearby null or reasonable length
        span = MEM[L:R]
        if 2 <= len(span) <= 40:
            # check if looks like text (high ratio of valid pairs)
            ctx = try_gbk_around(MEM, i, max(8, i - L + 4))
            # filter: must have at least one non-gaiji GBK char OR be adjacent to ascii text
            has_gbk = False
            j = L
            while j + 1 < R:
                code = (MEM[j] << 8) | MEM[j + 1]
                if not (0xA140 <= code <= 0xA14F) and 0x81 <= MEM[j] <= 0xFE:
                    try:
                        bytes([MEM[j], MEM[j + 1]]).decode("gbk")
                        has_gbk = True
                        break
                    except Exception:
                        pass
                j += 2
            if has_gbk or (L > 0 and MEM[L - 1] == 0) or (R < len(MEM) and MEM[R] == 0):
                lines.append("  VA=%08X span=%s" % (BASE + L, try_gbk_around(MEM, L, R - L)))
                found += 1
                if found > 200:
                    break
        i = R
    else:
        i += 1

text = "\n".join(lines)
open(OUT, "w", encoding="utf-8").write(text)
print("wrote", OUT, "lines", len(lines))
print(text[:8000])
