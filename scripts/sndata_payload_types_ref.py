# -*- coding: utf-8 -*-
"""sndata_payload_types_ref.py — 续183 破解 P0-B：SNDATA 真实类型 payload 类别目录（静态 + JSON 复核）

续176 已将 171 类型按 payload 形态归类为 二进制/word数组/状态开关。本文件把「具体哪些 type id 是
word 数组 / 状态开关」钉死为可复核目录，并附样本 payload，作为后续「逐 word 字段语义」工作的基座。

结论（续183 坐实）：
  * word 数组类型（payload 为 16-bit 字序列，field_probe 判 word数组）：id ∈ {15, 38, 75, 166, 214}
      - id=15 最常见（34 条），其余各 1 条；填充率 0.0~0.49 → 非纯文本、确为数值/索引数组。
  * 状态开关类型（payload 为布尔位标志，绝大多数字节为 0、尾部若干位=1）：id ∈ {0, 1}
      - id=0 样本 '...00000101'、id=1 样本 '...010101000101000101' → 场景状态布尔开关（续157/清单已标注）。

仍未知（续183 下一步，与续176 一致）：每个 word / 每个 bit 的具体字段含义 → 须 emu 驱动各 type 的
handler 簇（0x492e20/0x492ed0/...）或对照游戏，属独立深坑，不在本目录级条目范围。
"""
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = os.path.join(HERE, "sndata_type_schema.json")

WORD_ARRAY_IDS = {15, 38, 75, 166, 214}
STATUS_SWITCH_IDS = {0, 1}


def _t(name, cond):
    print(f"  [{'OK' if cond else 'NG'}] {name}")
    return bool(cond)


def main():
    ok = True
    d = json.load(open(SCHEMA))
    types = d["types"]

    wa_ids, ss_ids = [], []
    for tid, info in types.items():
        k = info.get("kind")
        if k == "word数组":
            wa_ids.append(int(tid))
        elif k == "状态开关":
            ss_ids.append(int(tid))

    ok &= _t("word 数组类型 = {15,38,75,166,214}", set(wa_ids) == WORD_ARRAY_IDS)
    ok &= _t("状态开关类型 = {0,1}", set(ss_ids) == STATUS_SWITCH_IDS)

    # id=15 最常见；其余各 1 条
    c15 = types.get("15", {}).get("count")
    ok &= _t("id=15 出现 34 条（最常见 word 数组）", c15 == 34)

    # 样本 payload 复核：word 数组样本须含多字（长度>4 字节）
    for tid in WORD_ARRAY_IDS:
        sp = types.get(str(tid), {}).get("sample_payload", "")
        ok &= _t("id=%d word 数组样本非空且为多字" % tid, len(sp) >= 8)

    # 状态开关样本：须含置位 bit（布尔开关特征，非全 0）
    for tid in STATUS_SWITCH_IDS:
        sp = types.get(str(tid), {}).get("sample_payload", "")
        ok &= _t("id=%d 状态开关样本含置位 bit（非全 0）" % tid, "1" in sp)

    print()
    print("word 数组类型目录:", sorted(wa_ids))
    print("状态开关类型目录:", sorted(ss_ids))
    print("结果：" + ("全部通过" if ok else "存在失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
