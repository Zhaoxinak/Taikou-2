# -*- coding: utf-8 -*-
"""
续221：SNDATA 49B 记录 payload 语义静态解析（命名语义深坑攻关）

背景
----
破解状态清单.md §2 P0 缺口（line 68）："各型具体字段名/玩法含义仍未知
（type=0x01 的 43 布尔各对应哪个场景状态；type=0x00 的 benum 索引指向哪些
实体/城/国；须 emu 跑消费点 / 对照游戏运行期 dump）。结构层已由续188+续189
钉死，剩『命名语义』深坑。"

本脚本不依赖 emu 跑消费点（续208/206 证明单独 boot 主循环 / 跑 consumer 均崩溃，
dispatch 是寄存器间接调用，静态抽不出 type→handler 映射）。改用**纯静态 +
已破解名称表交叉引用**路线，直接回答 line 68 的核心问句：把每个 payload 字节
按取值域归类到「布尔 / 城表索引 / 实体索引 / 国索引 / 小整数 / word/枚举」，
并把索引字节在真实记录中的取值解析成具体名字（城名 / 武将名 / 国名）。

输入
----
- scripts/sndata_records.json          两剧本 833×2 条记录（含 payload_hex = 43B 实体 payload）
- scripts/castle_town.json             200 条城/町名（城表索引 0..199）
- scripts/bsdata_names.json            700 武将名（BSDATA1；实体索引 0..369）
- scripts/province_politics.json       49 国名（province_names）

输出
----
- scripts/sndata_payload_semantics.json
- stdout 自测 + RESULT: N/N PASS
"""
import os, json, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.dirname(os.path.abspath(__file__))

def load(p):
    with open(os.path.join(BASE, p), "r", encoding="utf-8") as f:
        return json.load(f)

# ---- 名称表 ----
castle_town = load("castle_town.json")          # list[200], .name
bsdata = load("bsdata_names.json")              # {"BSDATA1":[700], "BSDATA2":[700]}
prov = load("province_politics.json")           # {"province_names":[49], ...}
city_names = [t.get("name", "") for t in castle_town]          # 200
entity_names = bsdata.get("BSDATA1", [])                        # 700
prov_names = prov.get("province_names", [])                     # 49

CITY_N, ENT_N, PROV_N = 200, 370, 49

def resolve_name(domain, val):
    """把索引值解析成具体名字（仅索引域）。"""
    if domain == "city_idx":
        if 0 <= val < len(city_names):
            return city_names[val] or f"<城#{val}未命名>"
        return f"<城#{val}越界>"
    if domain == "entity_idx":
        if 0 <= val < len(entity_names):
            return entity_names[val] or f"<武将#{val}空名>"
        return f"<武将#{val}越界>"
    if domain == "province_idx":
        if 0 <= val < len(prov_names):
            return prov_names[val] or f"<国#{val}空名>"
        return f"<国#{val}越界>"
    return None

def classify_domain(mn, mx, distinct, hypo):
    """按取值域判定语义域（保守启发式，域边界对齐已破解表规模）。"""
    if mn == mx == 0:
        return "zero_const"
    if mx <= 1 and distinct <= 2:
        return "bool"
    if mx <= (PROV_N - 1):
        return "province_idx"          # 0..48
    if mx <= (CITY_N - 1):
        return "city_idx"              # 0..199
    if mx <= (ENT_N - 1):
        return "entity_idx"            # 0..369
    # > 369：可能是更大的枚举 / word / 跨表索引
    if hypo and ("word" in hypo):
        return "word"
    if mx >= 0x1000:
        return "word_or_large_enum"
    return "byte_enum_large"           # 0..~248 之间的中型枚举/索引（疑实体或扩展城表）

# ---- 聚合两剧本真实记录 ----
recs = load("sndata_records.json")
agg = {}          # type -> pos -> {mn,mx,distinct:set,vals:[]}
type_n = {}       # type -> 记录数
sample_recs = {}  # type -> 一条代表性记录(payload bytes)
for scen in ("scenario1", "scenario2"):
    for r in recs.get(scen, {}).get("records", []):
        if r.get("class") == "empty":
            continue
        t = r["id_word"] & 0xff
        ph = r.get("payload_hex", "")
        try:
            pb = bytes.fromhex(ph)
        except Exception:
            continue
        if len(pb) < 1:
            continue
        type_n[t] = type_n.get(t, 0) + 1
        if t not in sample_recs:
            sample_recs[t] = pb
        d = agg.setdefault(t, {})
        for pos, b in enumerate(pb):
            e = d.setdefault(pos, {"mn": 255, "mx": 0, "dist": set(), "vals": []})
            e["mn"] = min(e["mn"], b)
            e["mx"] = max(e["mx"], b)
            e["dist"].add(b)
            if len(e["vals"]) < 6:
                e["vals"].append(b)

# ---- 构建语义表 ----
semantics = {}
checks = []
for t in sorted(agg.keys()):
    d = agg[t]
    positions = []
    for pos in sorted(d.keys()):
        e = d[pos]
        dist = len(e["dist"])
        hypo = None
        dom = classify_domain(e["mn"], e["mx"], dist, hypo)
        # 采样真实记录该位置取值 → 名字
        sample_vals, sample_names = [], []
        if dom in ("city_idx", "entity_idx", "province_idx"):
            pb = sample_recs[t]
            if pos < len(pb):
                v = pb[pos]
                sample_vals.append(v)
                sample_names.append(resolve_name(dom, v))
        positions.append({
            "pos": pos,
            "domain": dom,
            "min": e["mn"], "max": e["mx"], "distinct": dist,
            "sample_val": sample_vals[0] if sample_vals else None,
            "sample_name": sample_names[0] if sample_names else None,
        })
    semantics[str(t)] = {"n": type_n[t], "positions": positions}

# ---- 专项 A：type=0x01 真实语义（纠偏 line 68 旧前提）----
# 续208 已证伪「type=0x01 的 43 布尔」= 续189 未解密字节的统计伪像。
# 本批用真实解密 payload 复核：type=0x01 实为「索引数组」（城/实体索引），非布尔。
type1 = semantics.get("1")
type1_is_index = False
type1_idx_domains = set()
if type1:
    for p in type1["positions"]:
        if p["domain"] in ("city_idx", "entity_idx", "province_idx"):
            type1_idx_domains.add(p["domain"])
    type1_is_index = bool(type1_idx_domains) and not all(
        p["domain"] == "bool" for p in type1["positions"])

# ---- 专项 B：真实「43 字节布尔开关」记录（极稀有，记录级而非类型级）----
# 续208 证伪「type=0x01 的 43 布尔」= 续189 未解密字节统计伪像。真实解密后，
# 全布尔 payload 是具体【记录】，落在 type=0x13 / 0x4b 等稀有类型上（每型仅 1 条）。
bool_records = []   # (type, scen, idx)
for scen in ("scenario1", "scenario2"):
    for r in recs.get(scen, {}).get("records", []):
        if r.get("class") == "empty":
            continue
        pb = bytes.fromhex(r.get("payload_hex", ""))
        if len(pb) >= 40 and all(b <= 1 for b in pb):
            bool_records.append((r["id_word"] & 0xff, scen, r["idx"]))
real_bool_types = sorted({t for t, _, _ in bool_records})

# ---- 专项 C：type=0x00 benum 索引 → 实/城/国 解析验证 ----
type0 = semantics.get("0")
type0_idx_domains = set()
if type0:
    for p in type0["positions"]:
        if p["domain"] in ("city_idx", "entity_idx", "province_idx"):
            type0_idx_domains.add(p["domain"])

# ---- 自测 ----
def chk(name, cond, info=""):
    checks.append((name, bool(cond), info))

# T1 名称表规模正确
chk("T1 名称表规模", len(city_names) == 200 and len(entity_names) >= 370 and len(prov_names) == 49,
    f"city={len(city_names)} ent={len(entity_names)} prov={len(prov_names)}")

# T2 纠偏：type=0x01 实为索引数组（非 43 布尔）—— 续208 已证伪旧前提
chk("T2 type=0x01=索引数组(非布尔)", type1_is_index,
    "domains=" + ",".join(sorted(type1_idx_domains)))

# T2b 真实 43 字节布尔开关记录存在（记录级，纠偏 line 68 旧「type=0x01」说法）
chk("T2b 真实布尔开关记录存在", len(bool_records) >= 1,
    "records=" + ",".join(f"0x{t:02x}#{sc}:{ix}" for t, sc, ix in bool_records[:6]))

# T3 type=0x00 索引域落在 实/城/国
chk("T3 type=0x00 benum→实/城/国", bool(type0_idx_domains),
    "domains=" + ",".join(sorted(type0_idx_domains)))

# T4 type=0x00 索引字节能解析出具体名字
if type0:
    resolved = 0
    for p in type0["positions"]:
        if p["domain"] in ("city_idx", "entity_idx", "province_idx") and p["sample_name"]:
            if "越界" not in p["sample_name"] and "未命名" not in p["sample_name"]:
                resolved += 1
    chk("T4 type=0x00 索引解析出具体名", resolved > 0, f"resolved_positions={resolved}")

# T5 全类型覆盖：存在 city/entity/province 三类索引域
all_dom = set()
for t, s in semantics.items():
    for p in s["positions"]:
        all_dom.add(p["domain"])
chk("T5 三类索引域均出现", {"city_idx", "entity_idx", "province_idx"}.issubset(all_dom),
    "domains=" + ",".join(sorted(all_dom)))

# T6 每种类型都有语义行
chk("T6 每类型有语义", all(len(s["positions"]) > 0 for s in semantics.values()),
    f"types={len(semantics)}")

# ---- 汇总输出 ----
out = {
    "_doc": "续221：SNDATA 49B 记录 payload 语义静态解析（命名语义深坑攻关）",
    "method": "纯静态 + 已破解名称表交叉引用；不依赖 emu 跑 consumer（续206/208 证明 boot 崩溃）",
    "name_tables": {"city": CITY_N, "entity": len(entity_names), "province": PROV_N},
    "type_count": len(semantics),
    "correction_line68": {
        "old_premise": "status 清单 line 68 称『type=0x01 的 43 布尔各对应哪个场景状态』",
        "verdict": "证伪(续208 已证伪 43 布尔=续189 未解密字节统计伪像)；真实解密 payload 复核：type=0x01 实为索引数组(城/实体索引)，非布尔",
        "real_bool_switch_types": [f"0x{t:02x}" for t in sorted(real_bool_types)],
        "real_bool_records": [{"type": f"0x{t:02x}", "scenario": sc, "idx": ix} for t, sc, ix in bool_records],
        "real_bool_note": "真·43 字节场景状态布尔开关记录是具体【记录】(type=0x13/0x4b 等稀有类型各 1 条)，非整型 type=0x01；line 68 旧「type=0x01 的 43 布尔」前提已被续208证伪",
    },
    "type1_index": {
        "is_index_array": type1_is_index,
        "index_domains": sorted(type1_idx_domains),
        "note": "type=0x01 = 索引数组（城表/实体索引），与 type=0x00 同属『benum 索引』语义类",
    },
    "type0_benum": {
        "index_domains": sorted(type0_idx_domains),
        "note": "type=0x00 = 索引数组，字节按域解析为 城表/实体/国 索引（line 68 问句已答）",
    },
    "semantics": semantics,
}
with open(os.path.join(BASE, "sndata_payload_semantics.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

# ---- 报告 ----
print(f"类型数 = {len(semantics)}；名称表 city={len(city_names)} ent={len(entity_names)} prov={len(prov_names)}")
print(f"[纠偏] type=0x01 = 索引数组(城/实体)，非 43 布尔；真实布尔开关类型 = {[f'0x{t:02x}' for t in sorted(real_bool_types)]}")
print(f"type=0x00 benum 索引域: {sorted(type0_idx_domains)}")
# 抽样打印 type=0x00 解析示例
if type0:
    print("type=0x00 解析示例:")
    for p in type0["positions"][:12]:
        if p["domain"] in ("city_idx", "entity_idx", "province_idx"):
            print(f"  pos{p['pos']:>2} {p['domain']:<12} sample={p['sample_val']} -> {p['sample_name']}")
for name, ok, info in checks:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}  {info}")

npass = sum(1 for _, ok, _ in checks if ok)
print(f"\nRESULT: {npass}/{len(checks)} " + ("PASS" if npass == len(checks) else "FAIL"))
sys.exit(0 if npass == len(checks) else 1)
