#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_s1_unify_probe4.py -- 探针4：验证 w12 链的「同城」严格性 + 在 S2 城表(26B×200)里找链头字段。"""
import os, struct, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(ROOT, "Taikou2 Original")
SBASE = 0x58c
S1_OFF = SBASE + 22            # stream 22
S2_OFF = SBASE + 21852         # stream 21852
N1, STRIDE, NBS = 370, 59, 700
S2_N, S2_STRIDE = 200, 26


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
    s1 = [d[S1_OFF + i * STRIDE: S1_OFF + (i + 1) * STRIDE] for i in range(N1)]
    s2 = [d[S2_OFF + i * S2_STRIDE: S2_OFF + (i + 1) * S2_STRIDE] for i in range(S2_N)]
    w10 = [struct.unpack_from("<H", r, 0x10)[0] for r in s1]
    w12 = [struct.unpack_from("<H", r, 0x12)[0] for r in s1]
    kok = [r[0x30] for r in s1]   # 国
    joe = [r[0x31] for r in s1]   # 城

    print("=" * 78)
    print("SNDATA%d" % scen)
    targets = set(v for v in w12 if v < N1)
    heads = [i for i in range(N1) if i not in targets and w12[i] < N1]
    chains = []
    seen = set()
    for h in heads:
        ch, cur, g = [], h, 0
        while cur < N1 and cur not in seen and g < 400:
            seen.add(cur); ch.append(cur); cur = w12[cur]; g += 1
        chains.append(ch)

    # 1) 全链「同城/同国」严格性
    bad_city = [c for c in chains if len(set(joe[i] for i in c)) != 1]
    bad_kok = [c for c in chains if len(set(kok[i] for i in c)) != 1]
    print("  链数=%d 覆盖槽=%d ; 链内城不唯一的链=%d ; 链内国不唯一的链=%d"
          % (len(chains), len(seen), len(bad_city), len(bad_kok)))
    if bad_city:
        c = bad_city[0]
        print("    反例链=%s 城=%s" % (c[:10], [joe[i] for i in c[:10]]))

    # 2) 一城对一链？
    city_of_chain = [joe[c[0]] for c in chains]
    cc = collections.Counter(city_of_chain)
    print("  链→城 是否一一对应? %s ; 城重复top3=%s"
          % (len(cc) == len(chains), cc.most_common(3))) 

    # 3) 不在链上的有效槽：城值分布
    off_chain = [i for i in range(N1) if i not in seen and w10[i] != 0xffff]
    print("  有效但不在链上的槽=%d ; 其城值分布top5=%s"
          % (len(off_chain), collections.Counter(joe[i] for i in off_chain).most_common(5)))

    # 4) S2 城表里找「链头」字段：扫所有 word 偏移
    head_by_city = {joe[c[0]]: c[0] for c in chains}
    print("  链头城集合大小=%d" % len(head_by_city))
    for off in range(0, S2_STRIDE - 1):
        vals = [struct.unpack_from("<H", s2[c], off)[0] for c in range(S2_N)]
        hit = sum(1 for city, h in head_by_city.items() if city < S2_N and vals[city] == h)
        if hit >= max(3, len(head_by_city) // 4):
            print("    ★ S2 word@0x%02x 命中链头 %d/%d" % (off, hit, len(head_by_city)))
    # 也扫单字节偏移（链头 <370 需 2B，单字节只能覆盖 <256，仍试）
    for off in range(0, S2_STRIDE):
        vals = [s2[c][off] for c in range(S2_N)]
        hit = sum(1 for city, h in head_by_city.items() if city < S2_N and h < 256 and vals[city] == h)
        if hit >= max(3, len(head_by_city) // 4):
            print("    ☆ S2 byte@0x%02x 命中链头 %d/%d" % (off, hit, len(head_by_city)))

    # 5) 抽样打印 3 条链
    for c in sorted(chains, key=len, reverse=True)[:3]:
        print("  链(len=%2d) 国=%2d 城=%3d : %s"
              % (len(c), kok[c[0]], joe[c[0]],
                 " → ".join((gbk7(s1[i][0:7]) or "?") + (gbk7(s1[i][7:14]) or "") for i in c[:7])))
