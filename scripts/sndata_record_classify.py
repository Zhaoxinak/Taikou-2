# -*- coding: utf-8 -*-
"""
SNDATA 49B 剧本记录 —— 类型归类 + payload 采样（2026-08-31 续154 · 第一阶）

背景
----
SNDATA1/2.TR2 = 16B magic + 833×49B 记录 + 23B 尾（40856B）。
每条 49B 记录（反推自 0x47fc60 记录处理器读写模式）：
    [0:2]  id_word   (高低字节对称 ⇒ 填充哨兵；否则 低字节=类型, 高字节=实例号)
    [4:6]  sub_word
    [6]    flag
    [12:14] rel_word
    [6:49] 43B payload  (= 真实有效字节 real_byte_count，余为 0)

本脚本只做**静态归类**（免 emu），为后续逐类型破译 payload schema 打地基：
  1. 记录类型 = id_word & 0xff （实锤：对称 id_word 即填充哨兵）
  2. 按剧本识别填充哨兵类型
  3. 分离填充 / 有意义记录，列出有意义类型频次 + payload 样本
  4. 自校验：对称条数、填充计数、类型总数

参考实现策略：纯静态分析 sndata_records.json，无运行时依赖。
"""

import json
import os
import collections

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, "sndata_records.json")


# 填充哨兵类型（高低字节对称的「无数据」占位）
# 剧本1: 0x0c(尾张系默认) / 0xf3 / 0x0f / 0x00
# 剧本2: 0x0a / 0xf5 / 0x0f / 0x00
FILLER_TYPES = {
    "scenario1": {0x00, 0x0c, 0x0f, 0xf3},
    "scenario2": {0x00, 0x0a, 0x0f, 0xf5},
}


def rec_type(r):
    """记录类型 = id_word 低字节。"""
    return r["id_word"] & 0xFF


def is_symmetric(r):
    return (r["id_word"] & 0xFF) == (r["id_word"] >> 8)


def classify(scn, name=None):
    sc = scn["records"]
    filler = FILLER_TYPES.get(name or _scn_key(scn), set())
    types = collections.Counter(rec_type(r) for r in sc)
    sym = sum(1 for r in sc if is_symmetric(r))
    meaningful = [(t, c) for t, c in types.items() if t not in filler]
    meaningful.sort(key=lambda x: -x[1])
    n_meaningful = sum(c for _, c in meaningful)
    return {
        "total": len(sc),
        "symmetric": sym,
        "n_types": len(types),
        "filler_types": {hex(t): c for t, c in types.items() if t in filler},
        "n_meaningful_types": len(meaningful),
        "n_meaningful_recs": n_meaningful,
        "meaningful": meaningful,
    }


def _scn_key(scn):
    for k in FILLER_TYPES:
        if k in scn:
            return k
    return "scenario1"


def dump_meaningful_samples(scn, name=None, top_n=20, sample_per_type=3):
    """打印 TOP 有意义类型的 payload 样本（hex + 字节/字解析），供破译。"""
    sc = scn["records"]
    filler = FILLER_TYPES.get(name or _scn_key(scn), set())
    by_type = collections.defaultdict(list)
    for r in sc:
        t = rec_type(r)
        if t in filler:
            continue
        by_type[t].append(r)
    ranked = sorted(by_type.items(), key=lambda kv: -len(kv[1]))
    out = []
    for t, recs in ranked[:top_n]:
        out.append("类型 0x%02x (×%d):" % (t, len(recs)))
        for r in recs[:sample_per_type]:
            p = r["payload_hex"]
            ba = bytes.fromhex(p)
            # 尝试按 word 解析（小端）
            words = [ (ba[i] | (ba[i+1] << 8)) for i in range(0, len(ba)-1, 2) ]
            out.append("  idx%-4d sub=0x%04x flag=%d rel=0x%04x rbc=%d"
                       % (r["idx"], r["sub_word"], r["flag"], r["rel_word"], r["real_byte_count"]))
            out.append("    payload[%d] hex=%s" % (len(ba), p))
            out.append("    as words: %s" % " ".join("%04x" % w for w in words[:16]))
    return "\n".join(out)


def self_test():
    d = json.load(open(_SRC))
    results = []
    for scn_name, scn in d.items():
        c = classify(scn, scn_name)
        results.append((scn_name, c))
        print("== %s ==" % scn_name)
        print("  总数 %d | 对称id_word %d | 类型 %d 种" %
              (c["total"], c["symmetric"], c["n_types"]))
        print("  填充类型: %s" % c["filler_types"])
        print("  有意义: %d 种类型 / %d 条" % (c["n_meaningful_types"], c["n_meaningful_recs"]))
        print("  TOP 有意义: %s" % [(hex(t), n) for t, n in c["meaningful"][:10]])
        print()
    # 自校验断言
    assert results[0][1]["symmetric"] > 300, "对称条数应 >300（填充哨兵）"
    assert results[0][1]["n_meaningful_recs"] > 400, "有意义记录应 >400"
    assert "0xc" in results[0][1]["filler_types"], "剧本1 应有 0x0c 填充"
    print("自校验通过: 对称id_word / 填充计数 / 类型总数 一致 ✅")
    return results


if __name__ == "__main__":
    self_test()
    d = json.load(open(_SRC))
    print("\n" + dump_meaningful_samples(d["scenario1"], "scenario1", top_n=15, sample_per_type=2))
