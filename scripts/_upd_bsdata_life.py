# -*- coding: utf-8 -*-
"""回填 bsdata_spec.json: 生年/年齢编码定案 + 纠偏 @39@40@41 / @58 旧说。"""
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

d["birth_age_encoding"] = {
    "status": "✅ 定案(续131)",
    "birth_year": {
        "formula": "生年 = 1490 + (BSDATA @39 & 0x7F)   // 实体: 1490 + (byte[+0x1b] & 0x7F)",
        "base": 1490,
        "base_hex": "0x5d2",
        "range": "1493..1582 (全 700 条), 82 个不同值",
        "bit7": "独立 flag, 非生日位; 232/700 置位, 跨剧本 139 条翻转(90 置位/49 清除)",
    },
    "age": {
        "formula": "年齢(数え年) = (byte[0x5205F0] + 1560) − 生年 + 1",
        "getter": "0x49a5c0",
        "setter": "0x49a5e0 (按新年龄反设生年字段)",
        "setter_guard": "(byte[0x5205F0] − 年齢 + 1561) < 1490 ⇒ 不写入",
        "setter_idiom": "XOR 位域惯用法: dl=旧值; eax=(Y−age+1561+46); al^=dl; eax&=0x7f; "
                        "word[+0x1b] ^= ax  ⇒ 只替换低 7 位, bit7 原样保留",
        "setter_simplified": "new_low7 = (Y − 年齢 + 71) & 0x7F  (0x619+0x2e=1607; 1607−71=1536=0x600, &0x7f 下等价)",
        "inverse_consistency": "生年 = 今年 + 1 − 年齢 ⇔ getter 的数え年定义, 两者互为逆运算",
    },
    "offset_remap": "BSDATA @39 (off 0x27) → 运行时武将实体 +0x1b；两者编码相同但偏移不同, "
                    "存在一次带重映射的拷贝, 勿按同名偏移直查",
    "evidence": [
        "EXE 0x49a5c0: mov cl,byte[ecx+0x1b]; movzx ax,byte[0x5205f0]; and ecx,0x7f; "
        "add eax,0x618; add ecx,0x5d2; sub eax,ecx; inc eax; ret",
        "全镜像搜 4 字节立即数 1490(0x5d2) 仅 1 处命中, 即上述 add ecx,0x5d2",
        "史实锚点 21/21 全中（织田信长1534 / 武田信玄1521 / 上杉谦信1530 / 德川家康1542 / "
        "毛利元就1497 / 伊达政宗1567 / 真田幸村1567 / 石田三成1560 …）",
    ],
    "🔴_correction": "推翻续43/59「@39=生日月、@40=当前年龄、@41=生日年」。"
                     "@39 是生年；@40/@41 并非年龄/生日年（见下）。",
    "reference_impl": _ROOT + '/scripts/bsdata_lifespan_ref.py (220/220 PASS)',
}

d["refuted_hypotheses_131"] = {
    "@40": {
        "old": "当前年龄（续59: 跨剧本 +1）",
        "actual": "打包字段 @40 = 32*A + B, A=@40>>5∈0..7, B=@40&31∈0..31; "
                  "492/700 的 B=0, 跨剧本差值以 +4 为主(435 条)",
        "evidence": "corr(生年, @40&31)=+0.628, 但 max(0,生年−1548)==B 仅 510/700 "
                    "(纯 B=0 主群假象); 82 个生年中 41 个映射到多个 B",
        "verdict": "非年龄、非生日；真语义待定",
    },
    "@41": {
        "old": "生日年（续43）",
        "actual": "544/700 = 255 哨兵; 其余 156 条 0..253, 与生年/寿命均无相关性",
        "verdict": "非生日年；疑为剧本专属事件/登场槽, 待定",
    },
    "@43": {
        "old": "起始月（续43: 从开局回推的月数偏移, 0..62）",
        "actual": "82 个生年中有 71 个映射到多个 @43 ⇒ 不是生年的函数; "
                  "corr(生年,@43)=−0.015, corr(寿命,@43)=+0.028",
        "verdict": "「起始月」缺乏支撑, 应重新定性",
    },
    "@58": {
        "old": "初始预期寿命（续43: 8 档 {0,16,32,64,80,96,112,128}, 16 倍数）",
        "actual": "低 nibble 恒 0 ⇒ 实为 (高 nibble)<<4, 高 nibble∈{0,1,2,4,5,6,7,8}; "
                  "82 个生年中 64 个映射到多个 @58 ⇒ 非生年函数; "
                  "corr(寿命,@58)=−0.142, @58 分组下生年均值几乎相同(1529.8~1538.5)",
        "verdict": "「预期寿命」不成立；真语义待定",
    },
}

# 更新 still_unknown
d["still_unknown"] = [
    "@17 字段语义(2 bit 朝向?6 bit 备位) — 已知联合映射:@17=身份大类 2bit(@42=在世档, @57=身份码 0..7), "
    "universe={0,1,2}; 6 高位备位语义仍待钉",
    "🟡 @20/@21 NPC 关系初值(续44):与 @48/@57 无明显线性关系; 0x47d890 经核实是 49 字节 stride 的"
    "另一结构读取器(非 BSDATA, BSDATA 文件实测 41300=59×700 明文无头), 需另找访问器",
    "✅ [已破·续130] @27..29 与官方技能 10 项的精确位序 — **10 技能 × 2bit**:"
    "@27=技能0..3 / @28=技能4..7 / @29 低4位=技能8..9(高nibble 700/700恒0); "
    "与运行时实体 +0x0f/+0x10/+0x11 同构。🔴 推翻续55「5 技能×4bit nibble」旧说。"
    "参考实现 bsdata_fields_ref.py (1096/1096)",
    "🟡 [部分破·续131] 原「@39/@40/@41 生日三元组」: **@39 已定案 = 生年−1490**(低7位), "
    "bit7 为独立 flag; 年龄(数え年) = (byte[0x5205F0]+1560) − 生年 + 1, getter 0x49a5c0 / setter 0x49a5e0。"
    "🔴 但 @40/@41 并非年龄/生日年(见 refuted_hypotheses_131), 需另找语义。"
    "参考实现 bsdata_lifespan_ref.py (220/220)",
    "✅ @52 vs @56 俸禄档与俸禄等级独立字段(续41,详见 §field_correlations)",
    "🟡 @54/@55 = 隐藏 NPC 配置 flag(续42):@42=255 集中 13 条特殊配置 + 3 个在世特殊 NPC;位语义需 EXE 访问器钉",
    "🟡 [纠偏·续131] @58 非预期寿命: 实为 (高 nibble)<<4, nibble∈{0,1,2,4,5,6,7,8}; "
    "非生年函数(64/82 生年多值)且与寿命 corr 仅 −0.142。旧注「8 档 16 倍数寿命编码」不成立, 需重新定性",
]

d["reference_impl"] = ("scripts/bsdata_fields_ref.py (1096/1096 PASS); "
                       "scripts/bsdata_lifespan_ref.py (220/220 PASS)")

json.dump(d, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("written OK")
d2 = json.load(open(P, encoding="utf-8"))
print("JSON 合法; still_unknown", len(d2["still_unknown"]), "条, 已闭",
      sum(1 for x in d2["still_unknown"] if x.startswith("✅")))
print("birth_age_encoding.status:", d2["birth_age_encoding"]["status"])
print("refuted keys:", list(d2["refuted_hypotheses_131"].keys()))
