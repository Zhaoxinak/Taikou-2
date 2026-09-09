#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
export_for_godot.py — 太阁立志传2 原版数据 → Godot 友好 JSON 离线导出器

用途
----
把 `Taikou2 Original/` 下的原版二进制，按 docs/specs/GAME_DATA_SPEC.md 的
**权威布局（续200）** 解析，导出为 UTF-8 JSON 到 `data/`，供 Godot 运行时加载。

为什么需要它
------------
`scripts/bsdata.json` 是早期产物，其 `fields` 基于十进制猜测，已被续200 推翻：
  旧 `56=loyalty`   → 实为 16-bit 状态字低字节；忠诚真在 `0x35`
  旧 `50-51=trust`  → 实为功勲 `0x32-0x33`
  旧 `58=lifespan`  → 实为 `0x3a>>4` 主角槽
  旧 `16=face`      → 实为武将 ID
本脚本按正确布局重新解析，并内置样本断言。

用法
----
    cd "F:/Games/Taikou 2"
    python scripts/export_for_godot.py                    # 默认 scene 1 → ./data/
    python scripts/export_for_godot.py --scene 2          # BSDATA2.TR2
    python scripts/export_for_godot.py --out ./data       # 指定输出目录
    python scripts/export_for_godot.py --skip-text        # 跳过 6211 条文本（快）

输出
----
    data/officers.json   695 真实武将 + 5 占位（标记 is_placeholder）
    data/castles.json    200 城
    data/provinces.json  49 国
    data/items.json      物品表（若可用）
    data/names.json      名称总表 370 条
    data/skills.json     10 技能名
    data/text.json       6211 条 MSGX 文本（UTF-8）
    data/gaiji.json      外字替换表
    data/battles.json    38 张战图
    data/consts.json     全局常量

依赖：仅标准库。
"""

import argparse
import json
import os
import struct
import sys

# --------------------------------------------------------------------------
# 路径
# --------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
ORIGINAL_DIR = os.path.join(PROJECT_ROOT, "Taikou2 Original")

# --------------------------------------------------------------------------
# 常量（与 GAME_DATA_SPEC.md §1.2 / §3.3 一致）
# --------------------------------------------------------------------------
RECORD_SIZE = 59
OFFICER_COUNT = 700
REAL_OFFICER_COUNT = 695          # 695 真实 + 5 条 姓0NNN 占位槽

NONE_PROVINCE = 255
NONE_CITY = 255
RONIN_LORD = 0xFFFF
MERIT_MAX = 0xFFFF
FATHER_NONE = 0xFFFF

# 技能顺序（续237 静态实证）—— 注意是 算术/兵法，不是 算用/军学
SKILL_NAMES = ["口才", "马术", "算术", "剑术", "忍术", "兵法", "洋枪", "筑城", "礼法", "茶道"]

# 職位（byte[0x39] & 7）
RANK_NAMES = ["无", "足轻组头", "足轻工头", "足轻头", "家老", "组头", "家臣", "大名"]

# 五维顺序
FORCE_NAMES = ["lead", "martial", "domestic", "diplomacy", "charm"]
FORCE_CN = ["统率", "武力", "内政", "外交", "魅力"]

# 主角槽（byte[0x3a] >> 4）
ARCHETYPE_NAMES = {
    0: "木下藤吉郎", 1: "明智光秀", 2: "柴田胜家",
    4: "一般武将A", 5: "一般武将B", 6: "一般武将C",
    7: "织田信长", 8: "上杉谦信/本愿寺显如",
}

# --------------------------------------------------------------------------
# 外字（GAIJI.TR2，GBK 0xA140..0xA14F 被劫持）
# 续200/续247：在用的只有 5 槽
#   A141+A143+A144 = 長宗我部（元亲/信亲/盛亲）
#   A142+A143+A144 = 香宗我部（亲泰）
#   A147           = 垪（#182 垪和氏续）
# --------------------------------------------------------------------------
GAIJI_SINGLE = {
    0xA141: "長", 0xA142: "香", 0xA143: "宗我", 0xA144: "部",
    0xA147: "垪",
    0xA140: "堯", 0xA145: "籠", 0xA146: "頸", 0xA148: "惣",
    0xA149: "揆", 0xA14A: "梟", 0xA14B: "瓊", 0xA14C: "絆",
    0xA14D: "渚", 0xA14E: "戌",
}
# 三格连排 → 完整 4 字姓
GAIJI_TRIPLE = [
    ((0xA141, 0xA143, 0xA144), "長宗我部"),
    ((0xA142, 0xA143, 0xA144), "香宗我部"),
]


def decode_name_field(raw: bytes) -> str:
    """解码 7B 定长姓名槽（GBK + 外字）。返回 UTF-8 str。"""
    codes = []
    i = 0
    n = len(raw)
    while i + 1 < n:
        b0, b1 = raw[i], raw[i + 1]
        if b0 == 0x00 and b1 == 0x00:
            break
        code = (b0 << 8) | b1
        codes.append(code)
        i += 2

    # 先尝试三格连排匹配（4 字姓）
    out = []
    idx = 0
    while idx < len(codes):
        matched = False
        for pat, rep in GAIJI_TRIPLE:
            if tuple(codes[idx:idx + 3]) == pat:
                out.append(rep)
                idx += 3
                matched = True
                break
        if matched:
            continue
        code = codes[idx]
        if code in GAIJI_SINGLE:
            out.append(GAIJI_SINGLE[code])
        else:
            try:
                out.append(bytes([code >> 8, code & 0xFF]).decode("gbk"))
            except UnicodeDecodeError:
                out.append("\uFFFD")  # 无法解码
        idx += 1
    return "".join(out)


def unpack_skills(raw3: bytes) -> list:
    """10 技能 × 2 bit → [0..3] × 10（顺序见 SKILL_NAMES）。"""
    out = []
    for k in range(10):
        byte = raw3[k // 4]
        out.append((byte >> ((k & 3) * 2)) & 3)
    return out


# --------------------------------------------------------------------------
# BSDATA 解析
# --------------------------------------------------------------------------
def parse_bsdata(path: str) -> list:
    data = open(path, "rb").read()
    if len(data) != OFFICER_COUNT * RECORD_SIZE:
        raise ValueError(
            f"BSDATA 大小异常: {len(data)} != {OFFICER_COUNT}×{RECORD_SIZE}"
            f" = {OFFICER_COUNT * RECORD_SIZE}"
        )

    officers = []
    for i in range(OFFICER_COUNT):
        r = data[i * RECORD_SIZE:(i + 1) * RECORD_SIZE]

        bushou_id = struct.unpack_from("<H", r, 0x10)[0]
        compat = struct.unpack_from("<H", r, 0x14)[0]
        forces = {FORCE_NAMES[j]: r[0x16 + j] for j in range(5)}
        skills = unpack_skills(r[0x1B:0x1E])
        birth_year = 1490 + r[0x27]
        father_id = struct.unpack_from("<H", r, 0x29)[0]
        province = r[0x30]
        city = r[0x31]
        merit = struct.unpack_from("<H", r, 0x32)[0]
        lord = struct.unpack_from("<H", r, 0x36)[0]
        status_word = struct.unpack_from("<H", r, 0x38)[0]
        rank = (status_word >> 8) & 7          # ★ 必须 &7
        archetype = r[0x3A] >> 4

        officers.append({
            "id": i,
            "bushou_id": bushou_id,
            "surname": decode_name_field(r[0x00:0x07]),
            "given": decode_name_field(r[0x07:0x0E]),
            "compat": compat,
            "forces": forces,
            "skills": {SKILL_NAMES[k]: skills[k] for k in range(10)},
            "skill_levels": skills,
            "birth_year": birth_year,
            "father_id": father_id,
            "home_idx": r[0x2B],
            "stamina_max": r[0x2C],
            "stamina": r[0x2D],
            "stamina_drain": r[0x2E],
            "ambition": r[0x2F],
            "province": province,
            "city": city,
            "merit": merit,
            "salary": r[0x34],
            "loyalty": r[0x35],
            "lord": lord,
            "status_word": status_word,
            "rank": rank,
            "rank_name": RANK_NAMES[rank],
            "archetype": archetype,
            "archetype_name": ARCHETYPE_NAMES.get(archetype, "?"),
            "is_placeholder": i >= REAL_OFFICER_COUNT,
            "is_selectable": archetype in (0, 1, 2, 7, 8),
        })
    return officers


# --------------------------------------------------------------------------
# 自检：织田信长 / 木下藤吉郎
# --------------------------------------------------------------------------
def selfcheck(officers: list) -> None:
    errors = []

    # #13 织田信长
    n = officers[13]
    expect_forces = [96, 85, 92, 99, 90]     # 统率/武力/内政/外交/魅力
    got_forces = [n["forces"][k] for k in FORCE_NAMES]
    if got_forces != expect_forces:
        errors.append(f"#13 信长五维 {got_forces} != {expect_forces}")
    if n["rank"] != 7:
        errors.append(f"#13 信长職位 {n['rank']} != 7(大名)")
    if n["merit"] != 0xFFFF:
        errors.append(f"#13 信长功勲 {n['merit']:#x} != 0xffff")
    if n["salary"] != 250:
        errors.append(f"#13 信长俸禄 {n['salary']} != 250")
    if n["archetype"] != 7:
        errors.append(f"#13 信长主角槽 {n['archetype']} != 7")
    # 技能：马术3 洋枪3 茶道3 筑城2 兵法2 算术1 剑术1 口才1
    expect_sk = {"口才": 1, "马术": 3, "算术": 1, "剑术": 1,
                 "忍术": 0, "兵法": 2, "洋枪": 3, "筑城": 2, "礼法": 0, "茶道": 3}
    for k, v in expect_sk.items():
        if n["skills"][k] != v:
            errors.append(f"#13 信长技能 {k}={n['skills'][k]} != {v}")

    # #16 木下藤吉郎
    t = officers[16]
    expect_t = [84, 42, 89, 94, 97]
    got_t = [t["forces"][k] for k in FORCE_NAMES]
    if got_t != expect_t:
        errors.append(f"#16 藤吉郎五维 {got_t} != {expect_t}")
    if t["rank"] != 1:
        errors.append(f"#16 藤吉郎職位 {t['rank']} != 1(足轻组头)")
    if t["salary"] != 1:
        errors.append(f"#16 藤吉郎俸禄 {t['salary']} != 1")
    if t["archetype"] != 0:
        errors.append(f"#16 藤吉郎主角槽 {t['archetype']} != 0")

    # 全局值域
    for o in officers:
        if not (0 <= o["rank"] <= 7):
            errors.append(f'#{o["id"]} 職位越界 {o["rank"]}')
        if not (0 <= o["loyalty"] <= 100):
            errors.append(f'#{o["id"]} 忠诚越界 {o["loyalty"]}')
        if any(not (0 <= v <= 3) for v in o["skill_levels"]):
            errors.append(f'#{o["id"]} 技能越界 {o["skill_levels"]}')

    # 占位槽
    placeholders = [o for o in officers if o["is_placeholder"]]
    if len(placeholders) != 5:
        errors.append(f"占位槽 {len(placeholders)} != 5")

    # 外字姓
    gaiji_ids = [o["id"] for o in officers if any(
        c in "長香垪" for c in o["surname"])]
    if not set(gaiji_ids) & {182, 557, 568, 581, 583}:
        errors.append(f"外字姓记录未命中，实际={gaiji_ids}")

    if errors:
        print("\n[FAIL] 自检未通过：")
        for e in errors[:30]:
            print("   -", e)
        sys.exit(1)
    print(f"  [OK] 自检通过（武将 {len(officers)} 条，含 5 占位；外字姓 {gaiji_ids}）")


# --------------------------------------------------------------------------
# 其他数据
# --------------------------------------------------------------------------
def load_json(rel: str):
    p = os.path.join(SCRIPT_DIR, rel)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def build_castles():
    src = load_json("sndata_sections.json")
    if not src:
        return [], []
    castles = src.get("castle", [])
    names = src.get("castle_names", {})
    # EXE 名表（castle_names_exe.json，name_table[88+id]）只覆盖前 92 座城，
    # id 92..199 这 108 座在 sndata_sections.castle_names 里是 null —— 但它们有完整
    # 且各不相同的真实数据（国/農商/兵力/米/金/城主），是真城不是空槽。
    # 故对缺失项回退社区全量表 scripts/castle_names.json（200 条，来源 jcku / 星虎论坛）。
    comm = load_json("castle_names.json") or {}
    comm_names = {}
    for e in (comm.get("castles") or []):
        comm_names[str(int(e.get("id", -1)))] = e.get("name", "")
    out = []
    for i, c in enumerate(castles):
        rec = dict(c)
        rec["id"] = i
        nm = names.get(str(i), "")
        if not nm:
            nm = comm_names.get(str(i), "")
        rec["name"] = nm
        out.append(rec)
    return out, src.get("castle_fields", [])


def build_provinces():
    nt = load_json("name_table.json") or {}
    prov_names = nt.get("province_names", [])
    politics = load_json("province_politics.json")
    out = []
    for i, nm in enumerate(prov_names):
        out.append({"id": i, "name": nm})
    return out, politics


def build_battles():
    return load_json("hjmapdat_battles.json") or []


def build_text():
    m = load_json("msgx_all_texts.json")
    if not m:
        return {}
    return m.get("texts", {})


def build_gaiji():
    return {
        "note": "GBK 0xA140..0xA14F 被劫持为外字区；在用仅 5 槽",
        "single": {f"0x{k:04X}": v for k, v in GAIJI_SINGLE.items()},
        "triple": [
            {"codes": [f"0x{c:04X}" for c in pat], "text": rep}
            for pat, rep in GAIJI_TRIPLE
        ],
        "affected_officers": [182, 557, 568, 581, 583],
        "bitmap": "GAIJI.TR2 = 16×34B；u16 LE 源码 + 32B 16×16 1bpp（行主序 MSB 先行）",
    }


def build_consts():
    return {
        "OFFICER_COUNT": OFFICER_COUNT,
        "REAL_OFFICER_COUNT": REAL_OFFICER_COUNT,
        "OFFICER_RECORD_SIZE": RECORD_SIZE,
        "ENTITY_POOL_SLOTS": 370,
        "ENTITY_STRIDE": 47,
        "CASTLE_COUNT": 200,
        "PROVINCE_COUNT": 49,
        "MSGX_TOTAL": 6211,
        "BATTLE_MAPS": 38,
        "SFX_COUNT": 39,
        "BATTLE_UNIT_SLOTS": 15,
        "BATTLE_UNIT_STRIDE": 24,
        "ATK_DIVISORS": [10, 12, 15, 7, 7, 15, 100, 100,
                         10, 10, 12, 7, 7, 10, 10, 8,
                         100, 100, 12, 12],
        "MERIT_CAP": 60000,
        "STAMINA_CAP": 100,
        "FORCE_CAP": 100,
        "SKILL_CAP": 3,
        "NONE_PROVINCE": NONE_PROVINCE,
        "NONE_CITY": NONE_CITY,
        "RONIN_LORD": RONIN_LORD,
        "MERIT_MAX": MERIT_MAX,
        "FATHER_NONE": FATHER_NONE,
        "SKILL_NAMES": SKILL_NAMES,
        "RANK_NAMES": RANK_NAMES,
        "FORCE_NAMES": FORCE_NAMES,
        "FORCE_CN": FORCE_CN,
        "birth_year_base": 1490,
        "source": "docs/specs/GAME_DATA_SPEC.md §1.2（续200 权威布局）",
    }


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="太阁立志传2 → Godot 数据导出器")
    ap.add_argument("--scene", type=int, default=1, choices=[1, 2],
                    help="剧本 1 或 2（对应 BSDATA1/2.TR2）")
    ap.add_argument("--out", default=os.path.join(PROJECT_ROOT, "data"),
                    help="输出目录")
    ap.add_argument("--skip-text", action="store_true",
                    help="跳过 6211 条文本导出")
    ap.add_argument("--skip-battles", action="store_true",
                    help="跳过 38 张战图导出")
    args = ap.parse_args()

    out_dir = args.out
    os.makedirs(out_dir, exist_ok=True)

    def dump(name, obj):
        p = os.path.join(out_dir, name)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        size = os.path.getsize(p)
        print(f"  → {name:20s} {size:>10,} B")

    print(f"=== 太阁立志传2 → Godot 导出（剧本 {args.scene}）===")
    print(f"原版目录: {ORIGINAL_DIR}")
    print(f"输出目录: {out_dir}\n")

    # 1) 武将
    bs_path = os.path.join(ORIGINAL_DIR, f"BSDATA{args.scene}.TR2")
    if not os.path.exists(bs_path):
        print(f"[ERROR] 找不到 {bs_path}")
        sys.exit(1)
    print("[1/8] 解析武将主表 BSDATA…")
    officers = parse_bsdata(bs_path)
    selfcheck(officers)
    dump("officers.json", officers)

    # 2) 城
    print("[2/8] 导出城表…")
    castles, castle_fields = build_castles()
    if castles:
        dump("castles.json", {"fields": castle_fields, "castles": castles})
    else:
        print("  (跳过：sndata_sections.json 不可用)")

    # 3) 国
    print("[3/8] 导出国表…")
    provinces, politics = build_provinces()
    dump("provinces.json", {"provinces": provinces, "politics_raw": politics})

    # 4) 名称总表
    print("[4/8] 导出名称总表…")
    nt = load_json("name_table.json") or {}
    dump("names.json", nt)

    # 5) 技能
    print("[5/8] 导出技能名…")
    dump("skills.json", {
        "names": SKILL_NAMES,
        "cap": 3,
        "packing": "level_k = (byte[0x1b + k//4] >> ((k&3)*2)) & 3",
        "note": "正确名是 算术/兵法，不是 算用/军学（续211 实证）",
    })

    # 6) 外字 + 常量
    print("[6/8] 导出外字与常量…")
    dump("gaiji.json", build_gaiji())
    dump("consts.json", build_consts())

    # 7) 文本
    print("[7/8] 导出文本…")
    if args.skip_text:
        print("  (已跳过)")
    else:
        texts = build_text()
        if texts:
            dump("text.json", texts)
        else:
            print("  (跳过：msgx_all_texts.json 不可用)")

    # 8) 战图
    print("[8/8] 导出战图…")
    if args.skip_battles:
        print("  (已跳过)")
    else:
        battles = build_battles()
        if battles:
            dump("battles.json", battles)
        else:
            print("  (跳过：hjmapdat_battles.json 不可用)")

    print("\n=== 导出完成 ===")
    print(f"下一步：Godot 里用 DataLoader.gd 加载 {out_dir}/*.json")
    print("施工文档：docs/replication/Godot复刻实施方案.md")


if __name__ == "__main__":
    main()
