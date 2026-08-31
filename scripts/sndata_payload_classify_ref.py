# -*- coding: utf-8 -*-
"""
sndata_payload_classify_ref.py  —  P0 49B payload：全 833 条 per-type 字段指纹 + 三栏文本/二进制分类
====================================================================================================
承接续176（kind 分布：二进制164/word数组5/状态开关2）与续188（5 word 数组类型字节粒度纠偏）。

旧假设（笼统）：164 类二进制 payload「无结构、纯黑箱」。
本脚本推翻该笼统印象，给出**可操作的逐类型字段假设**：对 833 条记录按 type 聚类，逐字节位(0..42)
做统计指纹（常数字节 / 小域枚举 / 字节枚举 / 宽域索引），并判定每记录的 3 个重叠文本栏
(rec+6 / rec+19 / rec+32，对应 0x522c88/0x522c60/0x522c70) 是否承载可读文本（cp932）。

结论指向：
  (a) fill 主导型（0x0c/0xf3 等）= 记录填充/占位，真实字段极少；
  (b) 结构化小整数型（type=15 等）= 计数/枚举数组；
  (c) 文本栏型 = 场景/事件显示标签（3 重叠栏，display-only，不参与资源加载——印证续163/164/165）。

自测：T1 记录数==833；T2 word 数组 5 型计数符合续183/188；T3 fill 主导型 0x0c/0xf3 分类为二进制；
     T4 全量指纹表非空且覆盖所有出现类型。

运行：python sndata_payload_classify_ref.py   （从 scripts/ 目录）
"""
import os, struct, json
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SND = os.path.join(os.path.dirname(HERE), "Taikou2 Original", "SNDATA1.TR2")
WORDARRAY_TYPES = {15, 38, 75, 166, 214}
EXPECTED_WA_COUNTS = {15: 34, 38: 1, 75: 1, 166: 1, 214: 1}
FILL = {0x0C, 0xF3}


def parse_records(path):
    b = open(path, "rb").read()
    assert len(b) == 40856, f"unexpected SNDATA size {len(b)}"
    recs = []
    off = 16
    while off + 49 <= len(b):
        rec = b[off: off + 49]
        id_word = struct.unpack_from("<H", rec, 0)[0]
        sub_word = struct.unpack_from("<H", rec, 2)[0]
        flag_rel = struct.unpack_from("<H", rec, 4)[0]
        recs.append({
            "type": id_word & 0xFF,
            "id_word": id_word,
            "sub_word": sub_word,
            "flag_rel": flag_rel,
            "payload": rec[6:49],          # 43B 主体
        })
        off += 49
    return recs


def col_text(rec_bytes, start, maxlen):
    """模拟 strcpy(buf, &rec[start])：取到首个 NUL 或 maxlen。返回 (bytes, terminated)。"""
    seg = rec_bytes[start:start + maxlen]
    nul = seg.find(b"\x00")
    if nul == -1:
        return seg, False
    return seg[:nul], True


def cp932_readable(b):
    """判定字节串是否像可读 cp932(Shift-JIS) 文本。返回 (is_text, decoded_or_None)。

    严格启发式（避免把二进制字节巧合当成文本）：
      - 拒绝 U+FFFD（解码失败占位）；
      - 拒绝 PUA 私用区 (U+E000..U+F8FF) 与 C1 控制符（mojibake 特征）；
      - 非 ASCII 文本须含至少 1 个全角日文（平/片假名或汉字，ord>=0x3000），
        仅半角片假名（0x83xx 巧合）不足以判定为文本；
      - 纯 ASCII 须长度>=4 且含字母（词感）。
    """
    if len(b) < 2:
        return False, None
    try:
        s = b.decode("cp932")
    except UnicodeDecodeError:
        return False, None
    if "\ufffd" in s:
        return False, None
    # 拒绝 PUA 私用区 / C1 控制符（mojibake）
    if any((0xE000 <= ord(ch) <= 0xF8FF) or (0x80 <= ord(ch) <= 0x9F) for ch in s):
        return False, s
    printable = sum(1 for ch in s if ch.isprintable() or ch in "\t ")
    if printable / len(s) < 0.85:
        return False, None
    non_ascii = sum(1 for ch in s if ord(ch) >= 0x80)
    fullwidth_jp = sum(1 for ch in s if ord(ch) >= 0x3000)  # 平/片假名 + 汉字
    if non_ascii >= 1 and fullwidth_jp >= 1:
        return True, s
    if len(s) >= 4 and any(ch.isalpha() for ch in s):
        return True, s
    return False, s


def classify_column(rec_bytes, start, maxlen):
    seg, term = col_text(rec_bytes, start, maxlen)
    is_txt, dec = cp932_readable(seg)
    return {"raw": seg.hex(), "len": len(seg), "terminated": term,
            "is_text": is_txt, "decoded": dec}


def fingerprint(pls):
    """pls: list of 43-byte payloads。返回每字节位假设列表。"""
    n = len(pls)
    out = []
    for pos in range(43):
        vals = [p[pos] for p in pls]
        d = sorted(set(vals))
        mn, mx = d[0], d[-1]
        nd = len(d)
        if nd == 1:
            hypo = "const"
        elif mx <= 15 and nd <= 16:
            hypo = "small_int(0..15)"
        elif mx <= 31 and nd <= 32:
            hypo = "nibble_enum(0..31)"
        elif mx <= 255 and nd <= 48:
            hypo = "byte_enum/index"
        else:
            hypo = "wide(index/id)"
        out.append({"pos": pos, "distinct": nd, "min": mn, "max": mx,
                    "const_val": (d[0] if nd == 1 else None), "hypo": hypo})
    return out


def main():
    recs = parse_records(SND)
    n_total = len(recs)
    by_type = defaultdict(list)
    for r in recs:
        by_type[r["type"]].append(r)

    # 逐记录：3 栏分类
    per_record = []
    type_textcount = defaultdict(lambda: [0, 0, 0])  # type -> [col1,col2,col3] 文本计数
    type_fillratio = {}
    for r in recs:
        pb = r["id_word"].to_bytes(2, "little") + r["sub_word"].to_bytes(2, "little") + \
             r["flag_rel"].to_bytes(2, "little") + r["payload"]
        c1 = classify_column(pb, 6, 43)
        c2 = classify_column(pb, 19, 30)
        c3 = classify_column(pb, 32, 17)
        per_record.append({"type": r["type"], "id": r["id_word"],
                           "sub": r["sub_word"], "flag_rel": r["flag_rel"],
                           "c1": c1, "c2": c2, "c3": c3})
        tc = type_textcount[r["type"]]
        if c1["is_text"]:
            tc[0] += 1
        if c2["is_text"]:
            tc[1] += 1
        if c3["is_text"]:
            tc[2] += 1
        # fill ratio for this type (lazy)
    for t, lst in by_type.items():
        allb = [v for p in lst for v in p["payload"]]
        fr = sum(1 for v in allb if v in FILL) / len(allb)
        type_fillratio[t] = round(fr, 3)

    # 逐类型指纹（仅对 n>=2 的类型给完整指纹；n==1 给 fill 概览）
    type_fp = {}
    for t, lst in by_type.items():
        pls = [r["payload"] for r in lst]
        fp = fingerprint(pls)
        tc = type_textcount[t]
        type_fp[t] = {
            "n": len(lst),
            "fill_ratio": type_fillratio[t],
            "text_cols": {"c1": tc[0], "c2": tc[1], "c3": tc[2]},
            "fingerprint": fp,
        }

    # ---- 报告 ----
    print(f"=== SNDATA payload 全量分类（{n_total} 条 / {len(by_type)} 型）===\n")
    print("【TOP 出现类型】")
    top = sorted(by_type.items(), key=lambda kv: -len(kv[1]))[:12]
    for t, lst in top:
        tc = type_textcount[t]
        txt = sum(1 for x in (tc[0], tc[1], tc[2]) if x)
        print(f"  type=0x{t:02x}({t:3d})  n={len(lst):3d}  fill={type_fillratio[t]:.2f}  "
              f"文本栏 c1/c2/c3={tc[0]}/{tc[1]}/{tc[2]}")

    # 文本栏样本（取首个可读记录）
    print("\n【可读文本栏样本（cp932 解码）】")
    samples = 0
    for pr in per_record:
        for ci, c in (("c1", pr["c1"]), ("c2", pr["c2"]), ("c3", pr["c3"])):
            if c["is_text"] and c["decoded"]:
                print(f"  type=0x{pr['type']:02x} {ci}: {c['decoded']!r}  (raw={c['raw']})")
                samples += 1
                break
        if samples >= 20:
            break
    if samples == 0:
        print("  （无 cp932 可读文本——印证续176：payload 文本栏多为自定义编码/二进制）")

    # 结构化小整数型（非 fill、非 word 数组，但大量 small_int/nibble 字段）
    print("\n【结构化小整数型候选（fill<0.3 且含 small_int 字段）】")
    struct_cands = []
    for t, info in type_fp.items():
        if t in WORDARRAY_TYPES:
            continue
        if info["fill_ratio"] >= 0.3:
            continue
        small = sum(1 for f in info["fingerprint"] if f["hypo"].startswith("small") or f["hypo"].startswith("nibble"))
        if small >= 5:
            struct_cands.append((t, info["n"], info["fill_ratio"], small))
    for t, n, fr, small in sorted(struct_cands, key=lambda x: -x[3])[:15]:
        print(f"  type=0x{t:02x}({t:3d})  n={n:3d}  fill={fr:.2f}  small/nibble字段={small}/43")

    # ---- 自测 ----
    results = []
    # T1
    results.append(("T1 记录数==833", n_total == 833))
    # T2 word 数组计数
    wa_ok = all(type_fp.get(t, {}).get("n") == c for t, c in EXPECTED_WA_COUNTS.items())
    results.append(("T2 word数组5型计数符合续183/188", wa_ok))
    # T3 fill 主导型分类为二进制（无文本栏）
    t0c = type_fp.get(0x0C, {})
    tf3 = type_fp.get(0xF3, {})
    fill_ok = (t0c.get("fill_ratio", 0) > 0.5 and sum(t0c.get("text_cols", {}).values()) == 0 and
               tf3.get("fill_ratio", 0) > 0.5 and sum(tf3.get("text_cols", {}).values()) == 0)
    results.append(("T3 fill主导型0x0c/0xf3分类为二进制(无文本栏)", fill_ok))
    # T4 指纹表覆盖所有类型且非空
    t4 = len(type_fp) == len(by_type) and all("fingerprint" in v for v in type_fp.values())
    results.append(("T4 全量指纹表覆盖所有出现类型", t4))

    print("\n--- 自测 ---")
    for name, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")

    out = {
        "n_records": n_total,
        "n_types": len(by_type),
        "type_fp": {str(t): type_fp[t] for t in sorted(type_fp)},
        "top_types": [{"type": t, "n": len(lst)} for t, lst in
                      sorted(by_type.items(), key=lambda kv: -len(kv[1]))[:20]],
        "structured_smallint_candidates": [
            {"type": t, "n": n, "fill_ratio": fr, "small_fields": sm}
            for t, n, fr, sm in sorted(struct_cands, key=lambda x: -x[3])
        ],
    }
    jp = os.path.join(HERE, "sndata_payload_classify.json")
    json.dump(out, open(jp, "w"), ensure_ascii=False, indent=1)
    print(f"\n[written] {jp}")

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print(f"\n==== SUMMARY: {passed}/{total} PASS ====")
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
