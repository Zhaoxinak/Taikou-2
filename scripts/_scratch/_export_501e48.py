#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导出 0x501e48 表为 battle_units_spec.json。

已确认事实（反汇编证实）：
  - 该表被 0x41bf20 处的「军事/兵科管理对话框」构建函数引用，且全镜像中仅此一处引用。
  - 引用方式：mov esi,0x501e48; mov edi,0x10(16); 循环 16 次：push 2; push 8; push esi;
    call 0x47ad20(添加列表项,读 8 字节); add esi,0x30(=48); dec edi; jne。
  - 因此：16 条记录 × 48 字节，每条取前 8 字节作为列表项数据。
  - 每条 offset 24..31 恒为常量 [5,6,6,3,4,4,8,10]，疑似 8 项基础属性模板。

注意（诚实标注）：
  - 本表是 DIALOG/DISPLAY 数据，战斗模拟数学是否直接读它尚未经战斗路径(unicorn 实跑)确认。
  - 0x52d211 经反汇编证伪（是十进制→ASCII 派发函数，非数据表）。
"""
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>

import struct, json

BIN = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
ADDR = 0x501e48
STRIDE = 48
COUNT = 16

def load():
    with open(BIN, "rb") as f:
        return f.read()

def main():
    data = load()
    off = ADDR - BASE
    records = []
    for r in range(COUNT):
        base = off + r * STRIDE
        raw = data[base: base + STRIDE]
        u8 = list(raw)
        rec = {
            "index": r,
            "raw_hex": raw.hex(),
            "u8_all": u8,
            "header8": u8[0:8],          # 对话框循环实际读取的 8 字节
            "template8_const": u8[24:32],# 恒为 [5,6,6,3,4,4,8,10]
            "regionA_24": u8[0:24],
            "regionB_16": u8[32:48],
        }
        records.append(rec)

    # 检测 template8 是否全记录一致
    tmpl = records[0]["template8_const"]
    tmpl_consistent = all(rec["template8_const"] == tmpl for rec in records)

    # header8 随记录的变化（前 8 字节按记录）
    header_matrix = [rec["header8"] for rec in records]

    out = {
        "meta": {
            "source": "TAIK2W95.exe (脱壳镜像 scripts/_unpacked_mem.bin)",
            "address": "0x501e48",
            "stride_bytes": STRIDE,
            "record_count": COUNT,
            "referenced_by": "0x41bf20 军事/兵科管理对话框构建函数（全镜像唯一引用）",
            "access_pattern": "循环16次: push 2; push 8; push esi; call 0x47ad20; add esi,0x30; dec edi; jne",
            "interpretation": "候选 16 项兵种/阵形 目录表（展示+基础数据）；战斗数学是否直接读它待 unicorn 实跑确认",
            "status": "CONFIRMED_TABLE / SEMANTICS_PARTIAL",
        },
        "observed_constant_template8": tmpl,
        "template8_is_consistent_across_records": tmpl_consistent,
        "header8_per_record": header_matrix,
        "records": records,
        "notes": [
            "每条 48 字节；前 8 字节(header8)被对话框作为列表项读取，随记录从 [15]*8 递减到 [0,0,0,0,9,4,0,5]。",
            "offset 24..31 在所有 16 条中恒为 [5,6,6,3,4,4,8,10]，疑似 8 项基础属性/能力模板（数值 3-10，量级符合兵种基础值）。",
            "offset 0..23（24 字节）与 offset 32..47（16 字节）随记录变化，疑似等级/可用性/地形修正矩阵。",
            "0x52d211 已证伪：其为十进制→ASCII 派发函数（cmp al,N / mov bx,0xNNNN 链，索引1..34→'01'..'34'），非数据表。",
        ],
    }

    with open("battle_units_spec.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("已导出 battle_units_spec.json")
    print(f"  template8 = {tmpl}, 全记录一致={tmpl_consistent}")
    print(f"  header8[0]={header_matrix[0]}")
    print(f"  header8[15]={header_matrix[15]}")

if __name__ == "__main__":
    main()
