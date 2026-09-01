#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_s1_unify_probe5.py -- 探针5：孤立槽 vs 登场标志段；S2 word@0x00 与 word@0x05 是否同值。"""
import os, struct, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(ROOT, "Taikou2 Original")
SBASE = 0x58c
S1_OFF, S2_OFF = SBASE + 22, SBASE + 21852
N1, STRIDE, S2_N, S2_STRIDE = 370, 59, 200, 26


def load(n):
    return open(os.path.join(ORIG, n), "rb").read()


for scen in (1, 2):
    raw = load("SNDATA%d.TR2" % scen)
    k = raw[0x12] ^ raw[0x13]
    d = bytes(b ^ k for b in raw)
    s1 = [d[S1_OFF + i * STRIDE: S1_OFF + (i + 1) * STRIDE] for i in range(N1)]
    s2 = [d[S2_OFF + i * S2_STRIDE: S2_OFF + (i + 1) * S2_STRIDE] for i in range(S2_N)]
    w10 = [struct.unpack_from("<H", r, 0x10)[0] for r in s1]
    w12 = [struct.unpack_from("<H", r, 0x12)[0] for r in s1]
    flagA = raw[0x14:0x14 + 700]          # 明文段A：700B 登场标志
    flagB = raw[0x2d0:0x2d0 + 700]        # 明文段B：700B（0x14+700=0x2d0）

    targets = set(v for v in w12 if v < N1)
    heads = [i for i in range(N1) if i not in targets and w12[i] < N1]
    seen = set()
    for h in heads:
        cur, g = h, 0
        while cur < N1 and cur not in seen and g < 400:
            seen.add(cur); cur = w12[cur]; g += 1
    live = [i for i in range(N1) if w10[i] != 0xffff]
    iso = [i for i in live if i not in seen]

    print("=" * 78)
    print("SNDATA%d  key=0x%02x  有效槽=%d 链上=%d 孤立=%d" % (scen, k, len(live), len(seen), len(iso)))
    print("  段A(0x14) 值域=%s ; 段B(0x2d0) 值域=%s"
          % (sorted(set(flagA)), sorted(set(flagB))))
    for nm, seq in (("链上", sorted(seen)), ("孤立", iso)):
        fa = collections.Counter(flagA[w10[i]] for i in seq if w10[i] < 700)
        fb = collections.Counter(flagB[w10[i]] for i in seq if w10[i] < 700)
        print("  %s槽 → 段A[武将ID] 分布=%s ; 段B[武将ID] 分布=%s"
              % (nm, dict(fa), dict(fb)))
    # 段A 为 1 的武将总数 vs 有效槽数
    print("  段A==1 的武将数=%d ; 有效槽数=%d ; 链上槽数=%d"
          % (sum(1 for v in flagA if v == 1), len(live), len(seen)))
    # S2 两个链头字段是否恒等
    w0 = [struct.unpack_from("<H", s2[c], 0)[0] for c in range(S2_N)]
    w5 = [struct.unpack_from("<H", s2[c], 5)[0] for c in range(S2_N)]
    print("  S2 word@0x00 == word@0x05 全200城? %s ; 不等城数=%d"
          % (w0 == w5, sum(1 for c in range(S2_N) if w0[c] != w5[c])))
    nohead = [c for c in range(S2_N) if w0[c] >= N1]
    print("  S2 word@0x00 >=370(无链) 的城数=%d ; 其取值分布=%s"
          % (len(nohead), collections.Counter(w0[c] for c in nohead).most_common(3)))
