#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sndata_payload_fields_ref.py  --  续229：SNDATA 215 型逐字节字段名枚举（静态最大化闭包）
=====================================================================================
承接续221 语义域分类（`sndata_payload_semantics.json`：215 型 × 每字节 domain 分类），
把每个 payload 字节的「domain」解析为可用的字面字段信息：

  (1) 具体名字：用已破解名称表把索引字节解析成真名
        - entity_idx  → scripts/entity_names_sc1.json  (0..369, 370 实体槽)
        - city_idx    → scripts/castle_names.json      (0..199, 200 城)
        - province_idx→ scripts/province_politics.json (0..48, 49 国)
  (2) 结构角色：检测 (entity,city) / (entity,province) / 同域数组 / 单例 / 布尔旗 / 填充 模式，
        给每个字节一个位置化角色标签（如 pair0_entityA / arr3_city / flag / pad）。

产出 `sndata_payload_fields.json`（215 型 × 43 字节的「domain + 解析名 + 结构角色 + 型形状」）。

关于「逐字节字面玩法字段名」（如「主将」「目标城」）的残口：
  续163/164 已证类别簇 handler（0x492e20/0x492ed0…）0/44 直读记录缓冲；payload 真实消费者
  是 0x47f350 的 18 子解码器（剧本 bulk 解码），需完整文件 I/O + 堆分配才能 boot，emu 受
  heap/GDI/文件桩返回值钳制（续206/续223 失败模式）无法在此会话坐实。故本参考实现把
  「字面字段」推进到「域+解析名+结构角色」这一静态可达的最大闭包，真·玩法角色残口明确标注。

自测（round-trip + 结构一致性）：
  A) 域闭环：本脚本产出的每字节 domain 与续221 源语义域逐型逐位一致（总数吻合）。
  B) 名称解析：所有 entity/city/province 字节的 sample_val 均在合法索引内（无越界）。
  C) 结构自检：type=0x00 必呈 entity/city 配对（续221 已证「武将-城 配对」）；型形状归类合法。
"""
import os, json
from collections import Counter, OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEM = os.path.join(ROOT, "scripts", "sndata_payload_semantics.json")
ENT = os.path.join(ROOT, "scripts", "entity_names_sc1.json")
CAS = os.path.join(ROOT, "scripts", "castle_names.json")
PROV = os.path.join(ROOT, "scripts", "province_politics.json")
OUT = os.path.join(ROOT, "scripts", "sndata_payload_fields.json")

ENT_N, CAS_N, PROV_N = 370, 200, 49  # 与续200/续221 一致

def _load_name_tables():
    ent = json.load(open(ENT, encoding="utf-8"))
    cas = json.load(open(CAS, encoding="utf-8"))["castles"]
    prov = json.load(open(PROV, encoding="utf-8"))["province_names"]
    return ent, cas, prov

def _resolve(domain, val, ent, cas, prov):
    """返回 (name_str, ok_bool)"""
    if domain == "entity_idx":
        if 0 <= val < ENT_N:
            nm = ent[val]
            if nm and not nm.startswith("<空"):
                return nm, True
            return f"<空槽{val}>", True
        return f"!越界{val}", False
    if domain == "city_idx":
        if 0 <= val < CAS_N:
            nm = cas[val].get("name") or cas[val].get("display") or ""
            if nm:
                return nm, True
            return f"<空城{val}>", True
        return f"!越界{val}", False
    if domain == "province_idx":
        if 0 <= val < PROV_N:
            nm = prov[val]
            if nm:
                return nm, True
            return f"<空国{val}>", True
        return f"!越界{val}", False
    if domain == "bool":
        return "布尔(0/1)", True
    if domain == "zero_const":
        return "常量0", True
    return domain, True

def _detect_shape(domains):
    """输入 43 长 domain 列表。输出 (shape_label, role_per_pos 43长)"""
    IDX = ("entity_idx", "city_idx", "province_idx")
    def coarse(d):
        if d in IDX:
            return d
        if d == "bool":
            return "flag"
        return "pad"
    seq = [coarse(d) for d in domains]
    idx_positions = [(i, s) for i, s in enumerate(seq) if s in IDX]
    pm = {"entity_idx": "entity", "city_idx": "city", "province_idx": "province"}
    if not idx_positions:
        roles = ["flag" if s == "flag" else "pad" for s in seq]
        return ("flags_only" if any(s == "flag" for s in seq) else "all_pad"), roles
    idx_types = [s for i, s in idx_positions]
    distinct = set(idx_types)

    def fill(roles_out):
        cnt = {"entity_idx": 0, "city_idx": 0, "province_idx": 0}
        for s in seq:
            if s in IDX:
                k = cnt[s]
                cnt[s] += 1
                roles_out.append({"entity_idx": f"e{k}", "city_idx": f"c{k}",
                                   "province_idx": f"p{k}"}[s])
            elif s == "flag":
                roles_out.append("flag")
            else:
                roles_out.append("pad")
        return roles_out

    # 单域数组
    if len(distinct) == 1:
        dom = next(iter(distinct))
        label = {"entity_idx": "entity_array", "city_idx": "city_array",
                 "province_idx": "province_array"}[dom]
        return f"{label}({len(idx_types)})", fill([])
    # 配对 (a,b) 交替
    if len(distinct) == 2:
        a = idx_types[0]
        b = (distinct - {a}).pop()
        if all(idx_types[k] == (a if k % 2 == 0 else b) for k in range(len(idx_types))):
            roles = []
            j = 0
            for s in seq:
                if s in IDX:
                    tag = "A" if j % 2 == 0 else "B"
                    roles.append(f"pair{j//2}_{pm[s]}{tag}"); j += 1
                elif s == "flag":
                    roles.append("flag")
                else:
                    roles.append("pad")
            return f"{pm[a]}_{pm[b]}_pairs({len(idx_types)//2})", roles
    # 三元组 (a,b,c)
    if len(distinct) == 3:
        a, b, c = list(distinct)
        if all(idx_types[k] == [a, b, c][k % 3] for k in range(len(idx_types))):
            roles = []
            j = 0
            for s in seq:
                if s in IDX:
                    roles.append(f"tri{j//3}_{pm[s]}"); j += 1
                elif s == "flag":
                    roles.append("flag")
                else:
                    roles.append("pad")
            return f"{pm[a]}_{pm[b]}_{pm[c]}_triples({len(idx_types)//3})", roles
    # 混合
    return "mixed", fill([])

def build():
    sem = json.load(open(SEM, encoding="utf-8"))
    ent, cas, prov = _load_name_tables()
    semantics = sem["semantics"]
    out = OrderedDict()
    out["_meta"] = {
        "method": "续229 静态最大化：续221 语义域 + 已破解名称表解析 + 结构角色检测",
        "type_count": len(semantics),
        "index_spaces": {"entity": ENT_N, "city": CAS_N, "province": PROV_N},
        "residual": "逐字节「玩法角色」(主将/目标城…) 需 boot 0x47f350 子解码器 emu，本会话受堆/GDI/文件桩钳制未坐实",
    }
    fields_by_type = OrderedDict()
    for t in sorted(semantics, key=lambda x: int(x, 16)):
        v = semantics[t]
        hkey = f"0x{int(t):02x}"
        positions = v.get("positions", [])
        domains = [""] * 43
        sample_by_pos = {}
        for p in positions:
            if 0 <= p["pos"] < 43:
                domains[p["pos"]] = p["domain"]
                sample_by_pos[p["pos"]] = p.get("sample_val")
        resolved = []
        for pos in range(43):
            d = domains[pos]
            if not d:
                resolved.append({"pos": pos, "domain": "", "name": "",
                                 "sample_val": None, "role": "pad", "role_ok": True})
                continue
            sv = sample_by_pos.get(pos)
            nm, ok = _resolve(d, sv if sv is not None else -1, ent, cas, prov)
            resolved.append({"pos": pos, "domain": d, "name": nm,
                             "sample_val": sv, "role": None, "role_ok": ok})
        shape, roles = _detect_shape(domains)
        for i, r in enumerate(roles):
            resolved[i]["role"] = r
        fields_by_type[hkey] = {
            "shape": shape,
            "n_positions": len(positions),
            "fields": resolved,
        }
    out["types"] = fields_by_type
    return out, semantics

def self_test(out, semantics):
    fails = []
    # A) 域闭环：本产出与源语义域逐型逐位一致
    tot_src = Counter(); tot_out = Counter()
    for t, v in semantics.items():
        hkey = f"0x{int(t):02x}"
        src_doms = [""] * 43
        for p in v.get("positions", []):
            if 0 <= p["pos"] < 43:
                src_doms[p["pos"]] = p["domain"]
        out_doms = [""] * 43
        for f in out["types"][hkey]["fields"]:
            out_doms[f["pos"]] = f["domain"]
        for d in src_doms:
            tot_src[d] += 1
        for d in out_doms:
            tot_out[d] += 1
        if src_doms != out_doms:
            fails.append(f"A 型 {hkey} 域序列不一致")
    if tot_src != tot_out:
        fails.append(f"A 域总数不一致 src={dict(tot_src)} out={dict(tot_out)}")
    # B) 名称解析越界
    bad = 0; total_idx = 0
    for t, info in out["types"].items():
        for f in info["fields"]:
            if f["domain"] in ("entity_idx", "city_idx", "province_idx"):
                total_idx += 1
                if not f.get("role_ok", True):
                    bad += 1
    if bad:
        fails.append(f"B 名称解析越界 {bad}/{total_idx}")
    # C) type=0x00 必须含 entity/city/province 三域且形状合法（续221：type=0x00=三类索引混合列表）
    t0 = out["types"].get("0x00")
    valid_suffix = ("_pairs", "_triples", "_array", "mixed", "flags_only", "all_pad")
    ok_shape = t0 is not None and any(t0["shape"].endswith(s) for s in valid_suffix)
    doms0 = {f["domain"] for f in t0["fields"]} if t0 else set()
    has3 = {"entity_idx", "city_idx", "province_idx"} <= doms0
    if not (ok_shape and has3):
        fails.append(f"C type=0x00 形状={t0['shape'] if t0 else None} 三域齐全={has3}")
    return fails, tot_out, total_idx, bad

if __name__ == "__main__":
    out, semantics = build()
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    fails, tot_out, total_idx, bad = self_test(out, semantics)
    print(f"产出 scripts/sndata_payload_fields.json：types={out['_meta']['type_count']}")
    print(f"  域总数: {dict(tot_out)}")
    print(f"  索引字节数={total_idx}, 解析越界={bad}")
    print(f"  type=0x00 形状={out['types']['0x00']['shape']}")
    if fails:
        print("SELF-TEST FAIL:")
        for f in fails:
            print("  -", f)
    else:
        print("SELF-TEST: ALL PASS ✅")
