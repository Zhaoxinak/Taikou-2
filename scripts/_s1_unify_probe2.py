#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_s1_unify_probe2.py -- 探针2：S1(370×59) vs BSDATA(700×59) 逐偏移差异 + 0x0e/0x12 语义。"""
import os, struct, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(ROOT, "Taikou2 Original")
SBASE = 0x58c
S1_OFF = SBASE + 22
N1 = 370
STRIDE = 59


def load(n):
    return open(os.path.join(ORIG, n), "rb").read()


def dec(raw):
    k = raw[0x12] ^ raw[0x13]
    return bytes(b ^ k for b in raw)


def gbk7(b):
    b = b.split(b"\x00")[0]
    if not b:
        return None
    try:
        return b.decode("gbk")
    except Exception:
        return None


for scen in (1, 2):
    d = dec(load("SNDATA%d.TR2" % scen))
    bs = load("BSDATA%d.TR2" % scen)
    s1 = [d[S1_OFF + i * STRIDE: S1_OFF + (i + 1) * STRIDE] for i in range(N1)]
    b7 = [bs[i * STRIDE:(i + 1) * STRIDE] for i in range(700)]

    print("=" * 78)
    print("SNDATA%d S1 vs BSDATA%d[0:370] 逐偏移差异计数" % (scen, scen))
    diff = [sum(1 for i in range(N1) if s1[i][o] != b7[i][o]) for o in range(STRIDE)]
    nz = [(o, c) for o, c in enumerate(diff) if c]
    print("  完全相同的偏移数=%d/59；有差异的偏移=%s" % (STRIDE - len(nz), nz))
    print("  姓名段(0x00-0x0d)差异=%d" % sum(diff[0:14]))

    # 0x0e / 0x12 语义
    w0e = [struct.unpack_from("<H", r, 0x0e)[0] for r in s1]
    w10 = [struct.unpack_from("<H", r, 0x10)[0] for r in s1]
    w12 = [struct.unpack_from("<H", r, 0x12)[0] for r in s1]
    w36 = [struct.unpack_from("<H", r, 0x36)[0] for r in s1]
    b30 = [r[0x30] for r in s1]
    b31 = [r[0x31] for r in s1]
    for nm, v in (("0x0e", w0e), ("0x10", w10), ("0x12", w12), ("0x36", w36)):
        c = collections.Counter(v)
        print("  S1 w@%s distinct=%d min=%d max=%d top5=%s"
              % (nm, len(c), min(v), max(v), c.most_common(5)))
    print("  w10 == 记录索引 ? %s" % all(w10[i] == i for i in range(N1)))
    print("  w12 == w36 (主君) ? %s   相等条数=%d/370"
          % (w12 == w36, sum(1 for i in range(N1) if w12[i] == w36[i])))
    # 0x12 作为实体索引的合法性
    valid = [v for v in w12 if v < N1]
    print("  w12 <370 的条数=%d ；==0xffff 的条数=%d ；其它=%d"
          % (len(valid), sum(1 for v in w12 if v == 0xffff),
             sum(1 for v in w12 if v >= N1 and v != 0xffff)))
    # w0e 与「登场标志」段 (file 0x14, 700B) 的关系
    flag = load("SNDATA%d.TR2" % scen)[0x14:0x14 + 700]
    print("  登场标志段前370: 值域=%s ; w0e 与之相关? w0e!=0 且 flag=1 的条数=%d"
          % (sorted(set(flag[:N1])), sum(1 for i in range(N1) if w0e[i] and flag[i] == 1)))
    print("  S1 中 w0e 按值分组的样例: %s"
          % [(v, [i for i in range(N1) if w0e[i] == v][:4])
             for v, _ in collections.Counter(w0e).most_common(4)])
    # 主君指向自己=大名？
    self_lord = [i for i in range(N1) if w36[i] == i]
    print("  主君指向自己(=大名?) 条数=%d 索引前10=%s" % (len(self_lord), self_lord[:10]))
