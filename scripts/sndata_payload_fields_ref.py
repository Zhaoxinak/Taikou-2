# -*- coding: utf-8 -*-
"""
sndata_payload_fields_ref.py  —  P0 49B payload：word-array 类型「真实字段字节」定位
===================================================================================
承接 sndata_wordarray_payload_ref.py 的发现并**纠正续183「word 数组」标签**：

发现：续183 把 {15,38,75,166,214} 统称「word 数组」，但实测：
  - type=75 的 payload 是**干净**的 0x01/0x00 序列（无 0x0c/0xf3 填充）→ 真·位域/字数组；
  - type=15/38/166/214 的 payload **被 0x0c / 0xf3 填充字节主导**（如 type=15 43B 中
    0x0c×9 + 0xf3×5 = 14B 填充，占 33%），所谓「word」只是填充字节配对出的假象
    （0x0c0c=3084、0xf3xx≈62400 等）。⇒ 这些类型**不是干净 word 数组，而是稀疏结构**，
    真实数据只藏在少数「非填充」字节位。

本脚本：对 5 个类型逐字节位(0..42)判定「填充位」(恒 0x0c/0xf3) vs「真实位」(含非填充值)，
对真实位给出跨记录的取値分布，输出「真实字段字节位图」——这是「逐字段语义」的第一步硬证据。
自测：断言「仅 type=75 无填充；15/38/166/214 均含显著填充（纠正续183）」。

运行：python sndata_payload_fields_ref.py   （从 scripts/ 目录）
"""
import os, struct, json
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SND = os.path.join(os.path.dirname(HERE), "Taikou2 Original", "SNDATA1.TR2")
WORDARRAY_TYPES = {15, 38, 75, 166, 214}
FILL = {0x0C, 0xF3}


def parse_records(path):
    b = open(path, "rb").read()
    recs = []
    off = 16
    while off + 49 <= len(b):
        rec = b[off: off + 49]
        recs.append({"type": struct.unpack_from("<H", rec, 0)[0] & 0xFF,
                     "payload": rec[6:49]})
        off += 49
    return recs


def real_positions(payloads):
    """return list of (pos, fill_ratio, distinct_vals_sorted) for NON-fill positions."""
    n = len(payloads)
    res = []
    for pos in range(43):
        vals = [p[pos] for p in payloads]
        fillcount = sum(1 for v in vals if v in FILL)
        fr = fillcount / n
        if fr < 1.0:  # 至少一个记录该位非填充
            distinct = sorted(set(vals))
            res.append((pos, round(fr, 2), distinct))
    return res


def main():
    recs = parse_records(SND)
    by_type = {t: [r["payload"] for r in recs if r["type"] == t] for t in WORDARRAY_TYPES}
    results = []
    print(f"parsed {len(recs)} records\n")
    correction = {}
    for t in sorted(WORDARRAY_TYPES):
        pls = by_type[t]
        n = len(pls)
        # 整体填充率
        allbytes = [v for p in pls for v in p]
        fill_total = sum(1 for v in allbytes if v in FILL)
        fill_ratio = fill_total / len(allbytes)
        reals = real_positions(pls)
        is_clean = fill_ratio == 0.0  # 无填充 = 真·word/bit 数组
        correction[t] = {"n": n, "fill_ratio": round(fill_ratio, 3),
                         "real_pos_count": len(reals), "is_clean_wordarray": is_clean}
        print(f"--- type={t}  (n={n})  fill_ratio={fill_ratio:.3f}  "
              f"{'真·word/bit数组' if is_clean else '稀疏结构(含填充)'} ---")
        print(f"  真实字段字节位({len(reals)}个):")
        for pos, fr, distinct in reals:
            dsp = distinct if len(distinct) <= 16 else distinct[:16] + ["..."]
            print(f"    pos[{pos:2d}] 该位填充占比={fr:.2f}  取値={dsp}")
        print()

    # 自测
    # (a) 仅 type=75 是干净 word 数组（无填充）
    ok75 = correction[75]["is_clean_wordarray"] is True
    results.append(ok75)
    # (b) 15/38/166/214 均含显著填充（纠正续183 的“word 数组”统称）
    ok_sparse = all(correction[t]["fill_ratio"] > 0.05 for t in (15, 38, 166, 214))
    results.append(ok_sparse)

    print(f"  [{'PASS' if ok75 else 'FAIL'}] 仅 type=75 为干净 word/bit 数组(无填充)")
    print(f"  [{'PASS' if ok_sparse else 'FAIL'}] type=15/38/166/214 均含显著填充(非干净word数组,纠正续183)")

    out = os.path.join(HERE, "sndata_payload_fields.json")
    json.dump({"correction_to_续183": correction}, open(out, "w"), ensure_ascii=False, indent=1)
    print(f"\n[written] {out}")
    total = len(results); passed = sum(results)
    print(f"\n==== SUMMARY: {passed}/{total} PASS ====")
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
