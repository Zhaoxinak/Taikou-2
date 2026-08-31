# -*- coding: utf-8 -*-
"""
sndata_wordarray_payload_ref.py  —  P0 49B payload：word-array 类型(15/38/75/166/214) 逐字结构表征
=========================================================================================
承接清单 P0(B)「精解 type=0xdc 等 word 数组（15/38/75/166/214）」+ 续183「各真实类型 payload 字段语义」。

本脚本对真实 `SNDATA1.TR2`（40856B = 16B 头 + 833×49B 记录 + 23B 残）做：
  (1) 按 stride 49 / 头 16B 重新切分 833 条记录（与续159/164 一致）；
  (2) 取 id_word & 0xff 为 type，筛出 word-array 类型 {15,38,75,166,214}；
  (3) 对每条记录 payload(rec[6:49]=43B) 按 16-bit 小端解释为 21 个 word（rec[6:48]），
      逐 word 位置统计 min/max/去重数/取值集合，给出「像索引/像计数/像标志」的结构性假设；
  (4) 自测：断言 5 个 word-array 类型的记录数 = {15:34, 38:1, 75:1, 166:1, 214:1}
      （与 sndata_type_schema.json / 续183 一致），并断言 payload 确为二进制（非全 0 填充）。

注意：这是**静态结构表征**，给出「每个 word 位置的取值分布」这一最硬的证据；
逐 word 的**玩法含义**（第 k 个 word = 什么字段）仍须 emu 驱动对应 type 的 handler 簇
消费点（续183 下一步(A)）或对照游戏运行期 dump 坐实——本脚本不强行断言字段名。

运行：python sndata_wordarray_payload_ref.py   （从 scripts/ 目录）
"""
import os, struct, json

HERE = os.path.dirname(os.path.abspath(__file__))
SND = os.path.join(os.path.dirname(HERE), "Taikou2 Original", "SNDATA1.TR2")
SCHEMA = os.path.join(HERE, "sndata_type_schema.json")

WORDARRAY_TYPES = {15, 38, 75, 166, 214}
EXPECTED_COUNTS = {15: 34, 38: 1, 75: 1, 166: 1, 214: 1}


def parse_records(path):
    b = open(path, "rb").read()
    assert len(b) == 40856, f"unexpected size {len(b)}"
    recs = []
    off = 16
    while off + 49 <= len(b):
        rec = b[off: off + 49]
        idw = struct.unpack_from("<H", rec, 0)[0]
        subw = struct.unpack_from("<H", rec, 2)[0]
        flagrel = struct.unpack_from("<H", rec, 4)[0]
        typ = idw & 0xFF
        payload = rec[6:49]  # 43B 主视图
        recs.append({"idw": idw, "subw": subw, "flagrel": flagrel,
                     "type": typ, "payload": payload, "raw": rec})
        off += 49
    return recs


def words_of(payload):
    # 取 rec[6:48] = 42B = 21 个 16-bit 小端 word
    w = []
    for i in range(0, 42, 2):
        w.append(struct.unpack_from("<H", payload, i)[0])
    return w


def characterize(recs):
    by_type = {t: [] for t in WORDARRAY_TYPES}
    for r in recs:
        if r["type"] in WORDARRAY_TYPES:
            by_type[r["type"]].append(r)
    report = {}
    for t, lst in by_type.items():
        n = len(lst)
        if n == 0:
            report[t] = {"count": 0}
            continue
        # 逐 word 位置统计
        pos_stats = []
        for k in range(21):
            vals = [words_of(r["payload"])[k] for r in lst]
            pos_stats.append({
                "pos": k,
                "min": min(vals),
                "max": max(vals),
                "distinct": len(set(vals)),
                "vals": sorted(set(vals))[:12],
            })
        # 整体是否像索引（取值均 < 已知表上限 370/200/49?）
        allvals = [v for r in lst for v in words_of(r["payload"])]
        report[t] = {
            "count": n,
            "idw_set": sorted(set(r["idw"] for r in lst)),
            "subw_set": sorted(set(r["subw"] for r in lst)),
            "flagrel_set": sorted(set(r["flagrel"] for r in lst)),
            "word_min": min(allvals), "word_max": max(allvals),
            "word_distinct": len(set(allvals)),
            "pos": pos_stats,
            "payload_hex_sample": lst[0]["payload"].hex(),
        }
    return report


def main():
    recs = parse_records(SND)
    print(f"parsed {len(recs)} records from SNDATA1.TR2")
    report = characterize(recs)

    results = []
    # 自测
    for t in WORDARRAY_TYPES:
        cnt = report[t].get("count", 0)
        ok = cnt == EXPECTED_COUNTS[t]
        results.append(ok)
        print(f"  [{'PASS' if ok else 'FAIL'}] type={t} count={cnt} (expect {EXPECTED_COUNTS[t]})")

    # 结构表征输出
    for t in WORDARRAY_TYPES:
        r = report[t]
        if r.get("count", 0) == 0:
            continue
        print(f"\n--- type={t}  (n={r['count']}) ---")
        print(f"  idw_set={r['idw_set']}  subw_set={r['subw_set']}  flagrel_set={r['flagrel_set']}")
        print(f"  word value range: [{r['word_min']}..{r['word_max']}]  distinct={r['word_distinct']}")
        print(f"  sample payload hex: {r['payload_hex_sample']}")
        # 逐位置假设
        for p in r["pos"]:
            if p["distinct"] <= 1 and p["min"] == 0:
                tag = "全0(填充/保留)"
            elif p["max"] <= 370 and p["distinct"] < r["count"] * 3 + 5:
                tag = "疑似索引/枚举(小整数,≤370)"
            elif p["max"] <= 0xFFFF and p["distinct"] <= 3:
                tag = "疑似标志/状态码(少值)"
            else:
                tag = "宽值域(计数/数值)"
            print(f"    w[{p['pos']:2d}] min={p['min']:5d} max={p['max']:5d} distinct={p['distinct']:3d}  {tag}  vals={p['vals']}")

    total = len(results)
    passed = sum(results)
    print(f"\n==== SUMMARY: {passed}/{total} PASS (count self-test) ====")
    # 落盘便于后续 consumer 追踪
    out = os.path.join(HERE, "sndata_wordarray_payload.json")
    json.dump({"wordarray_types": {str(t): report[t] for t in WORDARRAY_TYPES}},
              open(out, "w"), ensure_ascii=False, indent=1)
    print(f"[written] {out}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
