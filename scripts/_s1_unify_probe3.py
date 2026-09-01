#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_s1_unify_probe3.py -- 探针3：按武将ID(stream 0x10)对齐 S1 槽 ↔ BSDATA 记录，再逐偏移比对。"""
import os, struct, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(ROOT, "Taikou2 Original")
SBASE, S1_OFF, N1, STRIDE, NBS = 0x58c, 0x58c + 22, 370, 59, 700


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
    b7 = [bs[i * STRIDE:(i + 1) * STRIDE] for i in range(NBS)]
    w0e = [struct.unpack_from("<H", r, 0x0e)[0] for r in s1]
    w10 = [struct.unpack_from("<H", r, 0x10)[0] for r in s1]
    w12 = [struct.unpack_from("<H", r, 0x12)[0] for r in s1]

    print("=" * 78)
    print("SNDATA%d" % scen)
    print("  w0e[i]==i 全条成立? %s" % all(w0e[i] == i for i in range(N1)))
    live = [i for i in range(N1) if w10[i] != 0xffff]
    print("  有效槽(w10!=0xffff)=%d ; w10 值域 min=%d max=%d ; 全部 <700? %s ; 互异? %s"
          % (len(live), min(w10[i] for i in live), max(w10[i] for i in live),
             all(w10[i] < NBS for i in live),
             len(set(w10[i] for i in live)) == len(live)))

    # 姓名一致性（按 ID 对齐）
    nm_ok = sum(1 for i in live if s1[i][0:14] == b7[w10[i]][0:14])
    print("  ★ 姓名段(0x00-0x0d) S1[i]==BSDATA[w10[i]] : %d/%d" % (nm_ok, len(live)))

    # 逐偏移差异（按 ID 对齐）
    diff = [sum(1 for i in live if s1[i][o] != b7[w10[i]][o]) for o in range(STRIDE)]
    same = [o for o in range(STRIDE) if diff[o] == 0]
    dnz = [(hex(o), diff[o]) for o in range(STRIDE) if diff[o]]
    print("  ★ 完全一致的偏移(%d个): %s" % (len(same), [hex(o) for o in same]))
    print("  ★ 有差异的偏移: %s" % dnz)

    # w12 语义探查
    tv = [w12[i] for i in range(N1) if w12[i] < N1]
    c = collections.Counter(tv)
    print("  w12 有效目标=%d 互异=%s 重复top3=%s" % (len(tv), len(c) == len(tv), c.most_common(3)))
    print("  w12[i]==i+1 ? %d 条 ; w12[i]==i ? %d 条"
          % (sum(1 for i in range(N1) if w12[i] == i + 1), sum(1 for i in range(N1) if w12[i] == i)))
    # 链表检测：从每个未被指向的槽出发走链
    targets = set(tv)
    heads = [i for i in range(N1) if i not in targets and w12[i] < N1]
    chains, seen = [], set()
    for h in heads:
        ch, cur, guard = [], h, 0
        while cur < N1 and cur not in seen and guard < 400:
            seen.add(cur); ch.append(cur); cur = w12[cur]; guard += 1
        chains.append(ch)
    print("  链头数=%d ; 链长分布top5=%s ; 覆盖槽=%d"
          % (len(heads), collections.Counter(len(c2) for c2 in chains).most_common(5), len(seen)))
    if chains:
        big = max(chains, key=len)
        print("  最长链 len=%d 前8槽=%s 对应姓名=%s"
              % (len(big), big[:8], [gbk7(s1[i][0:7]) or "?" for i in big[:8]]))
        # 该链上各槽的 国/城
        print("       国@0x30=%s" % [s1[i][0x30] for i in big[:12]])
        print("       城@0x31=%s" % [s1[i][0x31] for i in big[:12]])
