# -*- coding: utf-8 -*-
"""回填: 实体 +0x20..+0x23 定名(体力上限/体力/体力消耗/野心) + -12 通则 13 组验证。"""
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

t = d["entity_tail_method_table"]
t["fields"]["+0x20"] = "byte = **体力上限 (max HP)**, 钳 100 (setter 0x49a650)"
t["fields"]["+0x21"] = "byte = **体力（现役 / 当前 HP）** (setter 0x49a630, 29 调用); " \
                       "初始化 `+0x21 = +0x20`; 运行时 `+0x21 = min(+0x20, +0x21)` 钳到上限"
t["fields"]["+0x22"] = "byte = **体力消耗**, 钳 100 (setter 0x49a670)"
t["fields"]["+0x23"] = "byte = **野心**, 钳 100 (setter 0x49a690, 常量 0x32=50 / 0x50=80 / 0x64=100)"
t["vitals_evidence_134"] = {
    "method": "由续132 的「-12 通则」(实体偏移 = BSDATA 偏移 − 12) 反推，再用数据侧三重印证",
    "@44 → +0x20 体力上限": "setter `0x49a650` 含 `cmp 0x64` 钳 100；@44 实测 0..100、uniq=38 ✓",
    "@45 → +0x21 体力(现役)": "初始化路径 `movzx cx,byte[+0x20]; call 0x49a630` ⇒ 现役=上限；"
                              "@44 == @45 实测 700/700 ✓✓",
    "@46 → +0x22 体力消耗": "setter `0x49a670` 钳 100；@46 实测 ≤100、uniq=16 ✓",
    "@47 → +0x23 野心": "setter `0x49a690` 调用常量含 `0x32`(50)；@47 实测 **700/700 恒 50** ✓✓",
    "runtime_clamp": "0x4042a0: `movzx ax,byte[+0x21]; movzx cx,byte[+0x20]; cmp cx,ax; jae; "
                     "mov eax,ecx` ⇒ **+0x21 = min(+0x20, +0x21)**（当前体力不得高于上限）",
    "aging_or_damage": "0x404286: `push 0xa; push byte[+0x20]; call 0x4ebcd0` ⇒ "
                       "**体力上限每次 −10**（饱和减，0x4ebcd0: a>b 时返回 a−b），随后钳当前体力",
}
t["reference_impl"] = _ROOT + '/scripts/entity_tail_methods_ref.py (88/88 PASS)'

d["entity_offset_remap"]["verified_on"]["@44..@47 (体力/野心)"] = "→ 实体 +0x20..+0x23"
d["entity_offset_remap"]["verified_pairs"] = 13
d["entity_offset_remap"]["note"] = ("姓名区 @0..@13 不适用(会得负偏移), 名字经单独通道处理。"
                                    "⚠️ 目前仅在 @22..@47 区间被 13 组验证；向 @42/@52+ 外推须先核宽度"
                                    "（@52 俸禄阶梯最大 250，而按规则映射到的 +0x28 是 byte 钳 200，已不一致）")

d["reference_impl"] = ("scripts/bsdata_fields_ref.py (1096/1096 PASS); "
                       "scripts/bsdata_lifespan_ref.py (220/220 PASS); "
                       "scripts/entity_methods_ref.py (102/102 PASS); "
                       "scripts/entity_tail_methods_ref.py (88/88 PASS)")

json.dump(d, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("written OK")
d2 = json.load(open(P, encoding="utf-8"))
print("JSON 合法")
print("  +0x20:", d2["entity_tail_method_table"]["fields"]["+0x20"])
print("  +0x21:", d2["entity_tail_method_table"]["fields"]["+0x21"])
print("  +0x23:", d2["entity_tail_method_table"]["fields"]["+0x23"])
print("  remap verified_pairs:", d2["entity_offset_remap"]["verified_pairs"])
