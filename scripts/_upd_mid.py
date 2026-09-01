# -*- coding: utf-8 -*-
"""续136 回填: 实体中段方法表 + 身分名表 + @39..@42 第五组验证。"""
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

d["entity_mid_method_table"] = {
    "status": "✅ 定案(续136)",
    "range": "0x49a900 .. 0x49ae00 (第二个 setter 区段, 覆盖实体 +0x1b..+0x1e)",
    "fields": {
        "+0x1b": "byte = **生年字段**(BSDATA @39): 低 7 位 = 生年 − 1490; "
                 "**bit4/5/6/7 = 四个独立 or-flag** — setter `0x49ab00`/0x10(14 调用), "
                 "`0x49ab20`/0x20(4), `0x49ab40`/0x40(5), `0x49ab60`/0x80(17)。"
                 "**bit7 setter `0x49ab60` 正是续131 发现的『@39 bit7 flag』(232/700 置位、"
                 "跨剧本 139 条翻转)**。生年 setter `0x49a5e0` 用 XOR 惯用法保留这些位。",
        "+0x1c": "byte = **bits 2/3/4/5 四个独立 or-flag**(BSDATA @40) — "
                 "setter `0x49ab80`/0x04(6), `0x49aba0`/0x08(11), "
                 "`0x49abc0`/0x10(7), `0x49abe0`/0x20(1)。"
                 "🔴 续131 已推翻『@40 = 年龄』，本轮给出正解: **位域 flag 字节**。",
        "+0x1d": "byte = BSDATA @41, **钳 255** — setter `0x49ac00`(25 调用), "
                 "`and word[+0x1d], 0xff00` 清低字节后 `or min(v,0xff)`。"
                 "数据侧印证: @41 有 **544/700 = 255 哨兵** ✓",
        "+0x1e": "byte = BSDATA @42, **钳 255** — setter `0x49ac30`(17 调用), "
                 "`and word[+0x1d], 0xff` 清高字节后写入。"
                 "数据侧印证: @42 = 生死/状态枚举 **{0,1,2,255}** ✓",
        "+0x1f": "BSDATA @43 — setter 本轮未定位（开放项）",
    },
    "🔴_bit_aliasing_open": "年龄 getter `0x49a5c0` 用 `and ecx,0x7f` 取低 7 位，"
                           "而 bit4/5/6 的 setter(`0x49ab00/0x20/0x40`) **落在该掩码内** —— "
                           "置位会改变算出的年龄。只有 bit7(`0x49ab60`) 在掩码外、与年龄互不干扰。"
                           "可能 (a) 这三个 setter 属另一对象（该区段疑似混有多个对象方法），"
                           "或 (b) 确实存在位别名。⇒ 未验证前勿把 bits4-6 当生日位使用。",
    "reference_impl": _ROOT + '/scripts/entity_mid_fields_ref.py (41/41 PASS)',
}

d["rank_names_table"] = {
    "status": "✅ 定案(续136)",
    "base": "0x507778",
    "stride": 7,
    "count": 8,
    "values": ["浪人", "步兵头", "队长", "侍大将", "部将", "家老", "宿老", "大名"],
    "getter": "0x49a920",
    "formula": "身分名 = 0x507778 + 7 * ((word[+0x2c] >> 8) & 7)   "
               "(= 0x507778 + 7 * (byte[+0x2d] & 7))",
    "disasm": "mov cx,word[ecx+0x2c]; shr ecx,8; and ecx,7; "
              "mov eax,ecx; shl eax,3; sub eax,ecx (=7*ecx); add eax,0x507778; ret",
    "cross_validation": "交叉坐实续122 的『`+0x2d` 低 3 位 = 身分码 0..7 八档』"
                        "（+0x2d 即 word[+0x2c] 的高字节）",
    "note": "这正是太阁2 官方八段身分阶梯。表后紧跟 0x5077b0 起的另一张 stride7 表"
            "（'今井'/'津田'…，疑为茶人或商店名），故本表恰为 8 条。",
}

# 补 -12 通则第五组
d["entity_offset_remap"]["pairs"].append(
    {"bsd": "40..42", "ent": "+0x1c..+0x1e", "name": "状态 flag 字节 / @41 / @42",
     "evidence": "setter 族 0x49ab80..0x49abe0(+0x1c or-flag)、0x49ac00(+0x1d 钳255)、"
                 "0x49ac30(+0x1e 钳255)；@41 255 哨兵 544/700；@42 ⊂ {0,1,2,255}"}
)
d["entity_offset_remap"]["pairs"].append(
    {"bsd": "39..42", "ent": "+0x1b..+0x1e", "name": "生年字段（第五组验证）",
     "evidence": "0x49a5c0(年龄 getter) + 0x49ab60(@39 bit7 flag setter, 17 调用)"}
)

d["reference_impl"] = ("scripts/bsdata_fields_ref.py (1096/1096 PASS); "
                       "scripts/bsdata_lifespan_ref.py (220/220 PASS); "
                       "scripts/entity_methods_ref.py (102/102 PASS); "
                       "scripts/entity_tail_methods_ref.py (88/88 PASS); "
                       "scripts/bsdata_entity_remap_ref.py (49/49 PASS); "
                       "scripts/entity_mid_fields_ref.py (41/41 PASS)")

# 更新 still_unknown 第 3 项
for i, x in enumerate(d["still_unknown"]):
    if x.startswith("🟡 [部分破·续131]"):
        d["still_unknown"][i] = (
            "🟡 [大部分破·续131+续136] 原「@39/@40/@41 生日三元组」: "
            "**@39 = 生年字段**(低7位 = 生年−1490, bit4-7 为状态位, setter 0x49a5e0/0x49ab00-0x49ab60); "
            "**@40 = 位域 flag 字节**(bits2-5, setter 0x49ab80/0xa0/0xc0/0xe0), 🔴 非年龄; "
            "**@41 = byte 钳 255**(setter 0x49ac00, 25 调用), 544/700 = 255 哨兵; "
            "**@42 = 生死/状态枚举**(setter 0x49ac30, 17 调用)。"
            "仅 **@43**(→ 实体 +0x1f) 的 setter 未定位。参考实现 bsdata_lifespan_ref(220/220) + "
            "entity_mid_fields_ref(41/41)")

json.dump(d, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("written OK")
d2 = json.load(open(P, encoding="utf-8"))
print("JSON 合法")
print("  中段字段数:", len(d2["entity_mid_method_table"]["fields"]))
print("  身分名表  :", d2["rank_names_table"]["values"])
print("  通则 pairs:", len(d2["entity_offset_remap"]["pairs"]))
