# -*- coding: utf-8 -*-
"""回填 bsdata_spec.json: 闭合技能位序项 + 新增三张表 + 纠偏续55。"""
import json

P = "F:/Games/Taikou 2/scripts/bsdata_spec.json"
d = json.load(open(P, encoding="utf-8"))

# ---- 1. 替换 skill_mapping 为定案版
d["skill_mapping"] = {
    "source": "0x507b58(EXE 静态段, 5B×10 GBK, 续26 逐字节验证; 续130 dump 解码确认)",
    "official_order": ["口才", "马术", "算术", "剑术", "忍术", "兵法", "洋枪", "筑城", "礼法", "茶道"],
    "status": "✅ 定案(续130)",
    "packing": "10 技能 × 2 bit = 20 bit, 打包于 3 字节",
    "bsd_bit_layout": {
        "_": "BSDATA @27/@28/@29 与运行时武将实体 +0xf/+0x10/+0x11 是同一套打包(逐字节对应)",
        "27": {"skills": [0, 1, 2, 3], "bits": "0-1 / 2-3 / 4-5 / 6-7", "range": "0..255"},
        "28": {"skills": [4, 5, 6, 7], "bits": "0-1 / 2-3 / 4-5 / 6-7", "range": "0..255"},
        "29": {"skills": [8, 9], "bits": "0-1 / 2-3", "high_nibble": "未用(700/700 恒 0)", "range": "0..15"},
    },
    "entity_bit_layout": {
        "+0x0f": "技能0 口才(b0-1) / 1 马术(b2-3) / 2 算术(b4-5) / 3 剑术(b6-7)",
        "+0x10": "技能4 忍术(b0-1) / 5 兵法(b2-3) / 6 洋枪(b4-5) / 7 筑城(b6-7)",
        "+0x11": "技能8 礼法(b0-1) / 9 茶道(b2-3); 高4位未用",
    },
    "extraction": "skill_i = (byte[27 + i//4] >> (2*(i%4))) & 3   // BSDATA\n"
                  "skill_i = (byte[0x0f + i//4] >> (2*(i%4))) & 3 // 实体(需 +i//4 映射到 f/10/11)",
    "evidence": [
        "属性取值器 0x4c7c30: cmp ebx,0x13; ja -> jmp dword[ebx*4 + 0x4c7e84] (20 项跳表), "
        "各分支体直接给出字节/移位/&3 (attr13=+0xf&3 口才, attr5=+0xf>>2&3 马术, "
        "attr3=+0xf>>4&3 算术, attr12=+0x10&3 忍术, attr14=+0x10>>2&3 兵法, "
        "attr8=+0x10>>4&3 洋枪, attr9=+0x10>>6 筑城, attr10=+0x11&3 礼法, attr15=+0x11>>2&3 茶道)",
        "剑术 = byte[+0x0f]>>6: 0x4447948 'mov al,byte[edi+0xf]; shr al,6' 等 9 处",
        "数据侧: @29 高 nibble 700/700 恒 0",
        "史实锚点: 武田信玄/上杉谦信/毛利元就 兵法=3; 服部半藏 忍术=3 且 剑术=3",
    ],
    "🔴_correction": "推翻续55「BSDATA 3 字节只能存 5 技能(每 nibble 一个 4bit 技能)」。"
                     "实为 10 技能 × 2bit = 20bit, @27/@28 各 4 技能、@29 低4位 2 技能, "
                     "与运行时实体 +0xf..+0x11 完全同构。",
    "reference_impl": "scripts/bsdata_fields_ref.py (1096/1096 PASS)",
}

# ---- 2. 新增能力名表与属性评分表
d["ability_names"] = {
    "source": "0x507fc0, stride 7, 5 项 GBK (续130 dump 解码)",
    "values": ["统御力", "武力", "内政力", "外交力", "魅力"],
    "entity_offsets": {
        "+0x0d": "外交力 (硬证据: 0x4b5620 取 byte[+0xd] 后查 0x50c3cc='外交')",
        "+0x0e": "魅力   (硬证据: 0x4b5620 取 byte[+0xe] 后查 0x507fdc='魅力')",
        "+0x0b": "统御力/武力/内政力 之一 (待钉)",
        "+0x0c": "统御力/武力/内政力 之一 (待钉)",
        "note": "全镜像 byte[+0xa..+0x11] 的 mov 写入点 = 0 ⇒ setter 经 setAbility(char,idx,val) "
                "参数化, 静态不可见(MEMORY.md 已记的『只写用间接寻址』墙)",
    },
}

d["attr_score_table"] = {
    "getter": "0x4c7c30 (任务适性评分器: 遍历武将列表, 按属性 id 算分, 取最优)",
    "jump_table": "0x4c7e84, 20 项 (cmp ebx,0x13; ja ⇒ id 0..19)",
    "table": [hex(v) for v in [0x004C7CD7, 0x004C7CD7, 0x004C7CE5, 0x004C7D00, 0x004C7D11,
                               0x004C7D1B, 0x004C7D2D, 0x004C7D37, 0x004C7D41, 0x004C7D52,
                               0x004C7D61, 0x004C7D6F, 0x004C7D79, 0x004C7D88, 0x004C7D93,
                               0x004C7DA2, 0x004C7DB0, 0x004C7DD0, 0x004C7DEA, 0x004C7DFF]],
    "semantics": {
        "0/1": "身分码 = (word[+0x2c]>>8) & 7",
        "2": "外交力 + 口才*10",
        "3": "算术", "4": "能力@+0x0b", "5": "马术", "6": "能力@+0x0c", "7": "外交力",
        "8": "洋枪", "9": "筑城", "10": "礼法", "11": "魅力",
        "12": "忍术", "13": "口才", "14": "兵法", "15": "茶道",
        "16": "筑城*10 / (4-N)", "17": "能力@+0x0c / (4-N)",
        "18": "外交力 + 身分码*10", "19": "身分码 + 礼法*2",
    },
    "note": "N = 传入的除数参数(esp+0x1c 相关); 剑术未单独成项(仅出现在 BSDATA/位域), "
            "说明该表是「职务适性」评分而非「属性枚举」。",
}

# ---- 3. 闭合 still_unknown 第 3 项
d["still_unknown"] = [
    "@17 字段语义(2 bit 朝向?6 bit 备位) — 已知联合映射:@17=身份大类 2bit(@42=在世档, @57=身份码 0..7), "
    "universe={0,1,2}; 6 高位备位语义仍待钉",
    "🟡 @20/@21 NPC 关系初值(续44):与 @48/@57 无明显线性关系; 0x47d890 经核实是 49 字节 stride 的"
    "另一结构读取器(非 BSDATA, BSDATA 文件实测 41300=59×700 明文无头), 需另找访问器",
    "✅ [已破·续130] @27..29 与官方技能 10 项的精确位序 — **10 技能 × 2bit**:"
    "@27=技能0..3 / @28=技能4..7 / @29 低4位=技能8..9(高nibble 700/700恒0); "
    "与运行时实体 +0xf/+0x10/+0x11 同构。🔴 推翻续55「5 技能×4bit nibble」旧说。"
    "证据: 属性取值器 0x4c7c30 的 20 项跳表 0x4c7e84 + 0x4447948(shr 6 = 剑术) + "
    "史实锚点(武田信玄/上杉谦信/毛利元就 兵法=3, 服部半藏 忍术=3 剑术=3)。"
    "参考实现 bsdata_fields_ref.py (1096/1096)",
    "🟡 @39/@40/@41 生日三元组(续43):@43 ∈ [0..62] 为起始月;@39/@40/@41 三者联动精确粒度待 EXE 访问器钉",
    "✅ @52 vs @56 俸禄档与俸禄等级独立字段(续41,详见 §field_correlations)",
    "🟡 @54/@55 = 隐藏 NPC 配置 flag(续42):@42=255 集中 13 条特殊配置 + 3 个在世特殊 NPC;位语义需 EXE 访问器钉",
    "🟡 @58 预期寿命编码(续43):8 档 {0,16,32,64,80,96,112,128} 均为 16 倍数 → 与 @43 起始月换算为实际岁数需 EXE 钉",
]

d["reference_impl"] = "scripts/bsdata_fields_ref.py (1096/1096 PASS)"

json.dump(d, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("written OK")

d2 = json.load(open(P, encoding="utf-8"))
print("JSON 合法; still_unknown 项数:", len(d2["still_unknown"]))
print("skill_mapping.status:", d2["skill_mapping"]["status"])
print("ability_names.values:", d2["ability_names"]["values"])
print("attr_score_table 项数:", len(d2["attr_score_table"]["table"]))
