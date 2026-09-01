# -*- coding: utf-8 -*-
"""_bsdata_s1_probe.py — 续200 探针②：BSDATA 记录 schema == SNDATA S1 段 schema？

若成立，则 BSDATA*.TR2（明文 700 条）与 SNDATA S1（加密 370 条）共用
「0x47f7b0 实体初始化流」同一 59B 记录格式 —— 一次性坐实两文件族的关系。
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ORIG = os.path.join(ROOT, "Taikou2 Original")

STREAM_BASE = 0x58C      # 权威流基址（0x598 已作废，见 GAME_DATA_SPEC §3.17.6 续99）
S1_OFF, S1_N, STRIDE = 22, 370, 59


def load_sndata(fn):
    b = open(os.path.join(ORIG, fn), "rb").read()
    key = b[0x12] ^ b[0x13]
    dec = bytes(x ^ key for x in b[STREAM_BASE:])
    return b, key, dec


def gbk(bs):
    z = bytes(bs).split(b"\x00")[0]
    try:
        return z.decode("gbk")
    except Exception:
        return "<%s>" % bytes(bs).hex()


def name_of(rec):
    return gbk(rec[0:7]) + gbk(rec[7:14])


bs1 = open(os.path.join(ORIG, "BSDATA1.TR2"), "rb").read()
bs2 = open(os.path.join(ORIG, "BSDATA2.TR2"), "rb").read()
bsn1 = [name_of(bs1[i*59:(i+1)*59]) for i in range(700)]
bsn2 = [name_of(bs2[i*59:(i+1)*59]) for i in range(700)]

for fn, bsn in (("SNDATA1.TR2", bsn1), ("SNDATA2.TR2", bsn2)):
    raw, key, dec = load_sndata(fn)
    print("=== %s  key=0x%02x  stream_len=%d ===" % (fn, key, len(dec)))
    s1 = dec[S1_OFF: S1_OFF + S1_N * STRIDE]
    names = [name_of(s1[i*59:(i+1)*59]) for i in range(S1_N)]
    ok = [n for n in names if not n.startswith("<")]
    print("  S1 370 条：GBK 可解 %d / 370" % len(ok))
    print("  前 8 条:", names[:8])
    # 与 BSDATA 700 条比对
    inbs = sum(1 for n in names if n in bsn)
    print("  与同号 BSDATA 名表命中: %d / 370" % inbs)
    # 逐条同号比对（S1[i] 是否 == BSDATA[i]）
    same_idx = sum(1 for i in range(S1_N) if names[i] == bsn[i])
    print("  同索引逐条相等: %d / 370" % same_idx)
    # word +0x10 = 名表索引
    ids = [int.from_bytes(s1[i*59+0x10:i*59+0x12], "little") for i in range(S1_N)]
    print("  +0x10 (名表索引) 前 12:", ids[:12])
    print("  +0x10 == i 的条数:", sum(1 for i in range(S1_N) if ids[i] == i))
    print()

# 反向：BSDATA 的 700 条里，370 之后是什么？
print("=== BSDATA1 索引 365..375 与 690..699 ===")
for i in list(range(365, 376)) + list(range(690, 700)):
    r = bs1[i*59:(i+1)*59]
    print("  #%3d %-14s +0x10=%5d 五维=%s 身分=%d" % (
        i, bsn1[i], int.from_bytes(r[0x10:0x12], "little"),
        list(r[0x16:0x1b]), r[57]))
