# -*- coding: utf-8 -*-
"""回填: bsdata_spec 增实体尾段方法表; promo/promote3 记勲功上限 60000 已坐实。"""
import json

D = "F:/Games/Taikou 2/scripts/"

# ---------- 1. bsdata_spec: 实体尾段方法表
p = D + "bsdata_spec.json"
d = json.load(open(p, encoding="utf-8"))

d["entity_tail_method_table"] = {
    "status": "✅ 定案(续133)",
    "range": "0x49a5f0 .. 0x49a8b0 (武将实体尾段 +0x20..+0x2e 的 setter/getter 方法表)",
    "object": "同续132: 对象基址 = dword[0x513b14], 布局与实体表 0x519868(stride47) 一致",
    "fields": {
        "+0x20": "byte, 钳 100 (setter 0x49a650)",
        "+0x21": "byte (setter 0x49a630, 29 调用·最常用)",
        "+0x22": "byte, 钳 100 (setter 0x49a670)",
        "+0x23": "byte, 钳 100 (setter 0x49a690, 常量 50/80)",
        "+0x24": "byte = 被搜索匹配的目标 ID (setter 0x49a750; 续114 消费方 `cmp byte[+0x24],bl; je FOUND`)",
        "+0x25": "byte = 实体基础值 (setter 0x49a760; 续114 复制到 +0x13 / +0x18)",
        "+0x26": "word = 功勲/勲功, **钳 60000 (0xEA60)** (setter 0x49a770)",
        "+0x28": "byte, 钳 200 (setter 0x49a790)",
        "+0x29": "byte = **忠诚 loyalty, 钳 100** (setter 0x49a7b0; 续122 钳制点 0x49a7bf 正在此函数体内 ✓)",
        "+0x2a": "word, 哨兵 0xffff (setter 0x49a7d0)",
        "+0x2c": "word = 16-bit 状态字 (见 status_word)",
        "+0x2d": "byte = 状态字高字节 (bit3 flag / bit4 谋反 / bit7 已故)",
        "+0x2e": "byte = 1-byte 状态 (setter 0x49a880 / 0x49a8a0)",
    },
    "status_word_0x2c": {
        "bits 0-3": "低 nibble — getter 0x49a610 (`& 0xf`, `cmp 0xc` ⇒ <12 有效); "
                    "setter 0x49a6b0 用 XOR 惯用法 (`xor al,dl; and eax,0xf; xor word[+0x2c],ax`)",
        "bits 4-7": "四个独立 or-flag setter: 0x49a6d0/0x10, 0x49a6f0/0x20, 0x49a710/0x40, 0x49a730/0x80",
        "bits 11-13": "(= +0x2d bits 3-5) setter 0x49a7e0, 掩码 0xF8FF, 3-bit 域",
        "bits 13-14": "(= +0x2d bits 5-6) = **F2B 序列関係**, setter 0x49a840, "
                      "掩码 0x9FFF, `cmp 4` ⇒ 钳 0..3 (与续127「24 调用 {3:12,2:5,1:6}」吻合 ✓)",
        "bit 15": "(= +0x2d bit7) = **已故/除籍**, setter 0x49a860",
        "+0x2d bit3": "flag, setter 0x49a800 (续122/127 消费者 0x4a3ddf / 0x4e9beb)",
        "+0x2d bit4": "F4 谋反/背叛标记, setter **0x49a820**",
    },
    "🔴_entry_address_correction": "续127 把 F4 setter 记为 `0x49a828`——那是函数体地址；"
                                   "真实 e8 调用入口是 **0x49a820**（nop 滑橇之后）。"
                                   "本表一律用真实入口。同类坑见续92/续95。",
    "reference_impl": "scripts/entity_tail_methods_ref.py (64/64 PASS)",
}

d["reference_impl"] = ("scripts/bsdata_fields_ref.py (1096/1096 PASS); "
                       "scripts/bsdata_lifespan_ref.py (220/220 PASS); "
                       "scripts/entity_methods_ref.py (102/102 PASS); "
                       "scripts/entity_tail_methods_ref.py (64/64 PASS)")
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("bsdata_spec OK; 尾段方法表字段数:", len(d["entity_tail_method_table"]["fields"]))

# ---------- 2. promo / promote3: 勲功上限 60000 坐实
NEW = ("✅ [佐证·续133] 勲功字段定位: 武将实体 **word[+0x26] = 功勲/勲功**, setter `0x49a770` "
       "含 `cmp 0xEA60` ⇒ **上限 60000**, 与国力表 0x5259e8 上限(续104)同常量; "
       "故 0x4ebca0(勲功, ?, 60000) 中的 60000 即该字段上限(封顶)。"
       "原问: 0x4ebca0(勲功,?,60000) 的勲功增量语义")
for fn, keys in (("promo_spec.json", ("still_unknown", "open_questions")),
                 ("promote3_spec.json", ("still_unknown", "open_questions"))):
    fp = D + fn
    dd = json.load(open(fp, encoding="utf-8"))
    hit = 0
    for k in keys:
        if k not in dd:
            continue
        for i, x in enumerate(dd[k]):
            s = str(x)
            if "0x4ebca0" in s and "60000" in s and not s.startswith("✅"):
                dd[k][i] = NEW
                hit += 1
    json.dump(dd, open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    dd2 = json.load(open(fp, encoding="utf-8"))
    tot = sum(len(dd2.get(k, [])) for k in keys)
    closed = sum(1 for k in keys for x in dd2.get(k, []) if str(x).startswith("✅"))
    print(f"{fn}: 替换 {hit} 条; 已闭 {closed}/{tot}")
