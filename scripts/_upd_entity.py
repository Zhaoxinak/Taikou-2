# -*- coding: utf-8 -*-
"""回填 bsdata_spec: BSDATA↔实体偏移重映射通则 + 五维能力块定案。"""
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

import json

P = _ROOT + '/scripts/bsdata_spec.json'
d = json.load(open(P, encoding="utf-8"))

d["entity_offset_remap"] = {
    "status": "✅ 定案(续132)",
    "rule": "对 @22 及之后的数据字段: **实体偏移 = BSDATA 偏移 − 12 (0x0C)**",
    "verified_on": {
        "@22..@26 (五维能力)": "→ 实体 +0x0a..+0x0e",
        "@27..@29 (10 技能 2bit)": "→ 实体 +0x0f..+0x11",
        "@39 (生年)": "→ 实体 +0x1b",
    },
    "note": "姓名区 @0..@13 不适用(会得负偏移), 名字经单独通道处理。",
    "evidence": "续131 已证 生年 BSDATA@39 → 实体 +0x1b (差 12); "
                "续132 由能力 setter 族(+0x0a..+0x0e) 与技能 setter 族(+0x0f..+0x11) "
                "再次验证同一 -12 位移。",
}

d["entity_ability_block"] = {
    "status": "✅ 定案(续132) — 闭合续130 留的「+0x0b/+0x0c 待钉」",
    "block": "+0x0a..+0x0e (5 字节, 顺序与能力名表 0x507fc0 严格一致)",
    "mapping": {
        "+0x0a": "统御力", "+0x0b": "武力", "+0x0c": "内政力",
        "+0x0d": "外交力", "+0x0e": "魅力",
    },
    "hard_evidence": "+0x0d=外交力 / +0x0e=魅力 由 0x4b5620 查 0x50c3cc='外交'、"
                     "0x507fdc='魅力' 硬钉（续130）；其余三者由能力块的连续性 + "
                     "能力名表顺序对齐钉死。",
    "setter_family": "0x49a2b0 + 0x20*k (k=0..4), 各写 byte[ecx+k], 一律 "
                     "`cmp ax, 0x64; jbe` 钳制到 100；调用方传 ecx = base + 0x0a",
    "🔴_why_static_zero_writes": "全镜像 byte[reg+0x0b] 形式的 mov 写入点为 0 处，"
                                "原因是 setter 按 `ecx = base + N` **参数化传入偏移**，"
                                "函数体内只有 `mov byte[ecx+k], al`（k=0..4），"
                                "故静态扫描绝对偏移永远抓不到。续130 判为「须 emu」系误判。",
}

d["entity_method_table"] = {
    "status": "✅ 定案(续132)",
    "object_pointer": "dword[0x513b14] (武将对象基址)",
    "range": "0x49a2b0 .. 0x49a870 (规则间隔排布的方法表)",
    "entries": {
        "ability_setters": "0x49a2b0 + 0x20*k, k=0..4  → byte[base+0x0a+k], 钳 100",
        "skill_setters": "0x49a350/0x49a370/0x49a3a0/0x49a3d0 (+0x0f bit0/2/4/6); "
                         "0x49a400/0x49a420/0x49a450/0x49a480 (+0x10 bit0/2/4/6); "
                         "0x49a4b0/0x49a4d0 (+0x11 bit0/2)  → 钳 3",
        "skill_name_getters": "0x49a500 + 0x10*k, k=0..9 → 返回 0x507b58 + 5*k",
        "word8_setter": "0x49a5a0 (ecx = base+8) → word[ecx] bits 11-14",
        "age_getter": "0x49a5c0 → byte[+0x1b]",
        "birth_setter": "0x49a5e0 → byte[+0x1b] (XOR 位域惯用法)",
    },
    "caller_pattern": "调用点一律先 `mov reg, dword[0x513b14]` 再 `lea ecx,[reg+N]` / "
                      "`add ecx, N`, 然后 `push 值; call 方法`",
    "reference_impl": _ROOT + '/scripts/entity_methods_ref.py (102/102 PASS)',
}

d["reference_impl"] = ("scripts/bsdata_fields_ref.py (1096/1096 PASS); "
                       "scripts/bsdata_lifespan_ref.py (220/220 PASS); "
                       "scripts/entity_methods_ref.py (102/102 PASS)")

json.dump(d, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("written OK")
d2 = json.load(open(P, encoding="utf-8"))
print("JSON 合法")
print("  entity_offset_remap:", d2["entity_offset_remap"]["rule"])
print("  ability mapping   :", d2["entity_ability_block"]["mapping"])
print("  method table range:", d2["entity_method_table"]["range"])
print("  reference_impl    :", d2["reference_impl"])
