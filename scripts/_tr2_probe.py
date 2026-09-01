#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续199 探针：TR2 容器族结构分析（SAVEDATA / SNDATA / BSDATA）"""
import os, struct, collections

ORIG = os.path.join(os.path.dirname(__file__), "..", "Taikou2 Original")
def load(n): return open(os.path.join(ORIG, n), "rb").read()

SAVE = load("SAVEDATA.TR2")
SN1, SN2 = load("SNDATA1.TR2"), load("SNDATA2.TR2")
BS1, BS2 = load("BSDATA1.TR2"), load("BSDATA2.TR2")

print("=" * 70)
print("[1] SAVEDATA.TR2 槽几何验算  off = slot*40960 + 408")
print("=" * 70)
n = len(SAVE)
print("  filesize      = %d" % n)
print("  n - 408       = %d" % (n - 408))
print("  /40960        = %s" % ((n - 408) / 40960.0))
print("  整除          = %s  ⇒ 槽数 = %d" % ((n - 408) % 40960 == 0, (n - 408) // 40960))
print("  408 = 0x198   = 16(magic) + %d ; /8 = %s" % (408 - 16, (408 - 16) / 8.0))

print()
print("=" * 70)
print("[2] SAVEDATA 头部 408B：magic + 8 条槽元数据 (49B?)")
print("=" * 70)
print("  magic = %r" % SAVE[:16])
for s in range(8):
    o = 16 + s * 49
    rec = SAVE[o:o + 49]
    print("  slot%d @%3d: %s" % (s, o, rec[:24].hex()))
    try:
        txt = rec.decode("gbk", "replace")
    except Exception:
        txt = "?"
    # 抽可打印 GBK 片段
    segs, cur = [], b""
    for b in rec:
        if b >= 0xA1 or (0x20 <= b < 0x7F):
            cur += bytes([b])
        else:
            if len(cur) >= 2: segs.append(cur)
            cur = b""
    if len(cur) >= 2: segs.append(cur)
    print("        GBK: %s" % " | ".join(s2.decode("gbk", "replace") for s2 in segs))

print()
print("=" * 70)
print("[3] SAVEDATA 槽体：8 × 40960B，判空/占用")
print("=" * 70)
for s in range(8):
    o = 408 + s * 40960
    body = SAVE[o:o + 40960]
    nz = sum(1 for b in body if b)
    print("  slot%d @0x%06x: 非零 %6d/40960 (%.1f%%)  head=%s" %
          (s, o, nz, 100.0 * nz / 40960, body[:16].hex()))

print()
print("=" * 70)
print("[4] SNDATA1/2 与 BSDATA1/2 基本量")
print("=" * 70)
for nm, d in (("SNDATA1", SN1), ("SNDATA2", SN2), ("BSDATA1", BS1), ("BSDATA2", BS2)):
    print("  %-8s len=%6d  magic=%r  +0x10=%s" % (nm, len(d), d[:16], d[0x10:0x14].hex()))
print("  SNDATA len-16 = %d ; /49 = %s ; /47 = %s" %
      (len(SN1) - 16, (len(SN1) - 16) / 49.0, (len(SN1) - 16) / 47.0))
print("  slot 40960 - SNDATA 40856 = %d" % (40960 - len(SN1)))
print("  BSDATA len = %d ; -0 /49=%s /47=%s /41300 factors" %
      (len(BS1), len(BS1) / 49.0, len(BS1) / 47.0))

print()
print("=" * 70)
print("[5] SNDATA1 vs SNDATA2 差异分布（剧本 1/2）")
print("=" * 70)
diff = [i for i in range(min(len(SN1), len(SN2))) if SN1[i] != SN2[i]]
print("  差异字节数 %d / %d (%.1f%%)" % (len(diff), len(SN1), 100.0 * len(diff) / len(SN1)))
print("  首 20 处: %s" % [hex(x) for x in diff[:20]])
# 差异按 1KB 桶
buck = collections.Counter(x // 1024 for x in diff)
print("  按 1KB 桶 top10: %s" % buck.most_common(10))

print()
print("=" * 70)
print("[6] BSDATA1 vs BSDATA2 差异分布")
print("=" * 70)
diff2 = [i for i in range(min(len(BS1), len(BS2))) if BS1[i] != BS2[i]]
print("  差异字节数 %d / %d (%.2f%%)" % (len(diff2), len(BS1), 100.0 * len(diff2) / len(BS1)))
print("  全部位置: %s" % [hex(x) for x in diff2[:40]])
for x in diff2[:12]:
    print("    @0x%05x  BS1=%02x BS2=%02x" % (x, BS1[x], BS2[x]))

print()
print("=" * 70)
print("[7] SAVEDATA slot0 体 vs SNDATA1 相似度（存档是否内嵌剧本快照）")
print("=" * 70)
b0 = SAVE[408:408 + 40960]
for nm, d in (("SNDATA1", SN1), ("SNDATA2", SN2)):
    same = sum(1 for i in range(min(len(b0), len(d))) if b0[i] == d[i])
    print("  slot0 vs %s: 逐字节相同 %d/%d (%.1f%%)" % (nm, same, len(d), 100.0 * same / len(d)))
# 错位相关：去掉 16B magic
same = sum(1 for i in range(len(SN1) - 16) if b0[i] == SN1[16 + i])
print("  slot0[0..] vs SNDATA1[16..]: %d/%d (%.1f%%)" % (same, len(SN1) - 16, 100.0 * same / (len(SN1) - 16)))
