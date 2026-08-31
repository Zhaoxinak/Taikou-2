# -*- coding: utf-8 -*-
"""续135 回填: 撤销过窄边界、通则扩到 @22..@55、@53 由「武艺」改判「忠诚」。"""
import json

P = "F:/Games/Taikou 2/scripts/bsdata_spec.json"
d = json.load(open(P, encoding="utf-8"))

d["entity_offset_remap"] = {
    "status": "✅ 定稿(续135)",
    "rule": "**武将实体 = BSDATA 记录去掉前 12 字节姓名区**，即 `entity[i] = bsdata[i + 12]`，"
            "i ∈ [0, 47)。结构恒等式：**59 − 12 = 47 = 实体 stride**。",
    "applies_to": "@22 .. @55 （确认）；@56..@58 为**推定**（值域不冲突但证据不足）",
    "structural_identity": "59 - 12 = 47",
    "pairs": [
        {"bsd": "22..26", "ent": "+0x0a..+0x0e", "name": "五维能力", "clamp": 100,
         "evidence": "setter 族钳 100；实测 max ≤ 100"},
        {"bsd": "27..29", "ent": "+0x0f..+0x11", "name": "10 技能 ×2bit",
         "evidence": "@29 高 nibble 700/700 恒 0"},
        {"bsd": "31 / 49", "ent": "+0x13 / +0x25", "name": "現城 id（双写）",
         "evidence": "@31==@49 700/700 ↔ 续114 实测 `+0x13` 是 `+0x25` 的副本；哨兵 255 ↔ setter 常量 0xff"},
        {"bsd": "39", "ent": "+0x1b", "name": "生年", "evidence": "EXE 0x49a5c0 硬证据"},
        {"bsd": "44..47", "ent": "+0x20..+0x23", "name": "体力上限/体力/体力消耗/野心",
         "evidence": "@44==@45 700/700；@47 恒 50 ↔ setter 常量 0x32"},
        {"bsd": "48", "ent": "+0x24", "name": "親密度",
         "evidence": "@48=13 出现 57 次 ↔ setter 常量 0xd；@48=255 ↔ 常量 0xff"},
        {"bsd": "50..51", "ent": "+0x26 (word)", "name": "功勲", "clamp": 60000,
         "evidence": "非占位 max 30000 ≤ 60000"},
        {"bsd": "52", "ent": "+0x28", "name": "俸禄", "clamp": 200,
         "evidence": "非占位 max 200 = 钳 200"},
        {"bsd": "53", "ent": "+0x29", "name": "**忠诚**", "clamp": 100,
         "evidence": "max 100 = 钳 100；分布 top 100/89/88 均值高，符合忠诚"},
        {"bsd": "54..55", "ent": "+0x2a (word)", "name": "状态字",
         "evidence": "0xFFFF 占 674/700 ↔ +0x2a 哨兵"},
        {"bsd": "56..58", "ent": "+0x2c..+0x2e", "name": "状态/身份/寿命（推定）",
         "evidence": "值域不冲突，证据不足"},
    ],
    "🔴_key_resolution_135": "续134 曾因两组「越界」把通则边界收紧到 @22..@47，本轮证明是**假象**："
                              "@50..@51 > 60000 的值只有 0xFFFF（45 条），非哨兵 max = 30000；"
                              "@52 > 200 的值只有 250（同样 45 条）。"
                              "**两组越界是同一批 45 条占位记录**，非偏移错位 ⇒ 边界撤销，通则扩至 @22..@55。",
    "placeholder_records": {
        "count": 45,
        "marker": "@50..@51 == 0xFFFF（同时 @52 == 250）",
        "distinct_from": "BSDATA @42=255 的 544 条未启用槽（另一套标记，勿混）",
    },
    "🔴_correction_135": "原 spec 的 `@53 武艺/熟练度(?)` 是猜测；实为 **忠诚 loyalty**"
                          "（max 100 与 `+0x29` setter 钳 100 吻合，且续122 的钳制点 `0x49a7bf` "
                          "正落在 `0x49a7b0` 函数体内已坐实 `+0x29`=忠诚）。",
    "reference_impl": "scripts/bsdata_entity_remap_ref.py (49/49 PASS)",
}

# 修正 fields 里的 @53 描述
for f in d["fields"]:
    if f.get("off") == 53:
        f["name"] = "忠诚 loyalty"
        f["evidence"] = ("max=100 与实体 +0x29 setter 钳 100 吻合; 分布 top 100/89/88 均值高; "
                         "🔴 原记『武艺/熟练度』系猜测, 续135 改判为忠诚")
    if f.get("off") == 31:
        f["name"] = "現城 id (主源)"
    if f.get("off") == 49:
        f["name"] = "現城 id (冗余/双写)"

d["reference_impl"] = ("scripts/bsdata_fields_ref.py (1096/1096 PASS); "
                       "scripts/bsdata_lifespan_ref.py (220/220 PASS); "
                       "scripts/entity_methods_ref.py (102/102 PASS); "
                       "scripts/entity_tail_methods_ref.py (88/88 PASS); "
                       "scripts/bsdata_entity_remap_ref.py (49/49 PASS)")

json.dump(d, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("written OK")
d2 = json.load(open(P, encoding="utf-8"))
print("JSON 合法; pairs:", len(d2["entity_offset_remap"]["pairs"]))
print("applies_to:", d2["entity_offset_remap"]["applies_to"])
for f in d2["fields"]:
    if f.get("off") in (31, 49, 53):
        print(f"  @{f['off']}:", f["name"])
