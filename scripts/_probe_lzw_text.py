#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe: decompress every *.LZW in 'Taikou2 Original/' and classify as
TEXT (contains GBK strings) vs BINARY (image/sprite). Goal: locate the
"XOR 加密资源" event-text track that is NOT in MESSAGE*.LZW (MSGX).

Output per file:
  - magic (first 4 bytes)
  - if 'MSGX': n messages, list first few
  - else: count of printable GBK text runs (null-terminated) as a rough text indicator
"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from real_assets import ls11_decompress

ROOT = os.path.join(HERE, "..", "Taikou2 Original")

def gbk_runs(b):
    """Return list of non-empty null-terminated GBK-decoded strings >=2 chars."""
    out = []
    i = 0
    n = len(b)
    buf = bytearray()
    while i < n:
        c = b[i]
        if c == 0:
            if len(buf) >= 2:
                try:
                    s = bytes(buf).decode("gbk")
                    # keep only if mostly CJK / printable
                    if any(0x4e00 <= ord(ch) <= 0x9fff or ('a' <= ch <= 'z') or ('A' <= ch <= 'Z') for ch in s):
                        out.append(s)
                except Exception:
                    pass
            buf = bytearray()
            i += 1
            continue
        buf.append(c)
        i += 1
    return out

def main():
    files = sorted(f for f in os.listdir(ROOT) if f.lower().endswith(".lzw"))
    print(f"=== {len(files)} LZW files ===\n")
    text_files = []
    for f in files:
        raw = open(os.path.join(ROOT, f), "rb").read()
        try:
            dec = ls11_decompress(raw)
        except Exception as e:
            print(f"[ERR ] {f}: decompress failed: {e}")
            continue
        if not dec:
            print(f"[EMPTY] {f}: no output")
            continue
        magic = dec[:4]
        if magic == b"MSGX":
            n = struct.unpack_from("<H", dec, 4)[0]
            ptrs = [struct.unpack_from("<I", dec, 6 + i*4)[0] for i in range(n)]
            ptrs.append(len(dec))
            msgs = []
            for i in range(n):
                seg = dec[ptrs[i]:ptrs[i+1]]
                e = seg.find(b"\x00")
                if e >= 0: seg = seg[:e]
                try: msgs.append(seg.decode("gbk", "replace"))
                except Exception: msgs.append(repr(seg))
            # show first 3 non-trivial
            sample = [m for m in msgs if len(m) > 1][:3]
            print(f"[MSGX] {f}: {n} msgs | e.g. {sample}")
            text_files.append((f, n, "MSGX"))
        else:
            runs = gbk_runs(dec)
            longruns = [r for r in runs if len(r) >= 4]
            tag = "TEXT?" if len(longruns) >= 3 else "binary"
            sample = longruns[:3]
            print(f"[{tag:6}] {f}: dec={len(dec)}B runs={len(runs)} long={len(longruns)} | {sample}")
            if len(longruns) >= 3:
                text_files.append((f, len(longruns), "TEXT?"))
    print("\n=== TEXT-bearing LZW files (candidates for event text) ===")
    for f, c, k in text_files:
        print(f"  {f}: {c} ({k})")

if __name__ == "__main__":
    main()
