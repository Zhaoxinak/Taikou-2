#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gen_portraits.py — HD-2D 武将立绘提示词生成器（HD-4 执行器）

从 `data/officers.json` 读取 695 名武将，按角色属性（五维/職位/主角槽/生年）
生成 ImageGen 提示词，输出 JSON 供逐批生成 512×640 立绘。

风格基线（2026-09-08 用户确认）：**和风写实 HD-2D**
  = 高清像素 art + 真实日式甲胄质感 + Octopath Traveler 式光影

用法
----
    cd "F:/Games/Taikou 2"
    python scripts/gen_portraits.py                        # 全部 695 条
    python scripts/gen_portraits.py --priority             # 按优先级排（主角→大名→其他）
    python scripts/gen_portraits.py --start 0 --limit 50   # 第 1 批 50 条
    python scripts/gen_portraits.py --id 13                # 只看织田信长
    python scripts/gen_portraits.py --csv                  # 额外导出 CSV 便于人工审阅

输出
----
    tools/portrait_prompts.json   {count, style, negative, items:[{id,name,prompt,...}]}
"""

import argparse
import csv
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUT_DIR = os.path.join(PROJECT_ROOT, "tools")

# 游戏开局年份（用于估算角色年龄：织田信长 1534 生 → 26 岁）
BASE_YEAR = 1560

# ---------------------------------------------------------------------------
# 风格基线（★ 已用 sample_01_nobunaga_portrait.png 验证有效）
# ---------------------------------------------------------------------------
STYLE_PREFIX = (
    "HD-2D style portrait, Japanese Sengoku warlord, "
    "half-body, 4:5 vertical composition, "
    "high-resolution pixel art with realistic Japanese aesthetics, "
)

STYLE_SUFFIX = (
    "Octopath Traveler HD-2D aesthetic, "
    "soft rim lighting, warm amber color palette, "
    "detailed armor texture and fabric folds, "
    "sharp clean pixel edges, dramatic cinematic lighting, "
    "game character portrait"
)

NEGATIVE = (
    "blurry, photorealistic, 3D render, western armor, modern clothing, "
    "smooth gradients, anti-aliased pixels, low resolution, jpeg artifacts, "
    "watermark, text, multiple characters"
)

# ---------------------------------------------------------------------------
# 属性 → 描述词
# ---------------------------------------------------------------------------
RANK_DESC = {
    0: "rankless ronin, plain traveling clothes",
    1: "ashigaru squad leader, light lacquer armor",
    2: "ashigaru engineer, practical work armor",
    3: "ashigaru captain, sturdy leather armor",
    4: "karou elder retainer, formal court armor",
    5: "kumi-gashira captain, well-crafted armor",
    6: "senior retainer, fine samurai armor",
    7: "daimyo warlord, elaborate armor with gold accents",
}

ARCHETYPE_DESC = {
    0: "humble origin, clever sharp eyes, thin build",      # 木下藤吉郎
    1: "refined intelligent features, composed",            # 明智光秀
    2: "veteran warrior, blunt honest face, heavy build",   # 柴田胜家
    7: "ambitious conqueror, commanding aura",              # 织田信长
    8: "pious warlord, devout expression",                  # 上杉谦信 / 本愿寺显如
}


def age_desc(birth_year: int) -> str:
    age = BASE_YEAR - birth_year
    if age < 20:
        return "youthful, about %d years old" % max(age, 14)
    if age <= 35:
        return "in his prime, about %d years old" % age
    if age <= 50:
        return "middle-aged, about %d years old" % age
    return "older weathered veteran, about %d years old" % age


def force_desc(forces: dict) -> list:
    """按五维追加描述（取最高的若干项）"""
    out = []
    m = forces.get("martial", 0)
    l = forces.get("lead", 0)
    c = forces.get("charm", 0)
    d = forces.get("domestic", 0)
    p = forces.get("diplomacy", 0)

    if m >= 90:
        out.append("battle-worn armor, fierce expression, scars")
    elif m >= 75:
        out.append("seasoned warrior look, hardened gaze")

    if l >= 90:
        out.append("commanding presence, authoritative posture")
    elif l >= 75:
        out.append("natural leader bearing")

    if c >= 90:
        out.append("refined noble features, charismatic smile")

    if d >= 90:
        out.append("scholarly air, court attire accents")
    elif d >= 75:
        out.append("intelligent thoughtful eyes")

    if p >= 90:
        out.append("composed diplomat, elegant manner")

    # 全部平庸
    if not out:
        out.append("ordinary samurai, plain appearance")
    return out


def build_prompt(o: dict, province_name: str) -> str:
    parts = [STYLE_PREFIX]

    parts.append(age_desc(o.get("birth_year", BASE_YEAR - 30)) + ",")

    rank = o.get("rank", 0)
    parts.append(RANK_DESC.get(rank, "samurai") + ",")

    if province_name:
        parts.append("clan of %s," % province_name)

    arch = o.get("archetype", -1)
    if arch in ARCHETYPE_DESC:
        parts.append(ARCHETYPE_DESC[arch] + ",")

    parts.append(", ".join(force_desc(o.get("forces", {}))) + ",")

    parts.append(STYLE_SUFFIX)
    return " ".join(p for p in parts if p)


def priority_key(o: dict) -> tuple:
    """排序：可选主角 → 大名 → 職位高 → 五维和高"""
    return (
        0 if o.get("is_selectable") else 1,
        0 if o.get("rank", 0) == 7 else 1,
        -o.get("rank", 0),
        -sum(o.get("forces", {}).values()),
    )


def main():
    ap = argparse.ArgumentParser(description="HD-2D 武将立绘提示词生成器")
    ap.add_argument("--start", type=int, default=0, help="起始索引")
    ap.add_argument("--limit", type=int, default=0, help="条数（0=全部）")
    ap.add_argument("--priority", action="store_true", help="按优先级排序")
    ap.add_argument("--id", type=int, default=None, help="只生成指定武将 id")
    ap.add_argument("--csv", action="store_true", help="额外导出 CSV")
    ap.add_argument("--out", default=None, help="输出路径")
    args = ap.parse_args()

    # 载入数据
    off_path = os.path.join(DATA_DIR, "officers.json")
    if not os.path.exists(off_path):
        print("[ERROR] 找不到 %s，请先运行 scripts/export_for_godot.py" % off_path)
        sys.exit(1)
    officers = json.load(open(off_path, encoding="utf-8"))

    provinces = []
    prov_path = os.path.join(DATA_DIR, "provinces.json")
    if os.path.exists(prov_path):
        provinces = json.load(open(prov_path, encoding="utf-8")).get("provinces", [])

    castles = []
    cas_path = os.path.join(DATA_DIR, "castles.json")
    if os.path.exists(cas_path):
        castles = json.load(open(cas_path, encoding="utf-8")).get("castles", [])

    def province_of_officer(o: dict) -> str:
        """地理所属国：officer.city → 城表[city].province → 国名表[province].name

        ⚠️ 注意：officer['province']（BSDATA 0x30）是「氏族/大名序号」，并非地理国名
        （例如织田信长该字段=13，对应国名表[13]=骏河，显然错误）。
        地理国名必须经由 居城 → 城表.province 推导。
        浪人（city=255/None）或缺失城表时返回 ''。
        """
        city = o.get("city")
        if isinstance(city, int) and 0 <= city < len(castles):
            p = castles[city].get("province")
            if isinstance(p, int) and 0 <= p < len(provinces):
                return provinces[p].get("name", "")
        return ""

    # 过滤
    pool = [o for o in officers if not o.get("is_placeholder", False)]
    if args.id is not None:
        pool = [o for o in pool if o["id"] == args.id]
        if not pool:
            print("[ERROR] 未找到武将 id=%s" % args.id)
            sys.exit(1)

    if args.priority:
        pool.sort(key=priority_key)

    end = len(pool) if args.limit <= 0 else min(len(pool), args.start + args.limit)
    pool = pool[args.start:end]

    items = []
    for o in pool:
        pname = province_of_officer(o)
        items.append({
            "id": o["id"],
            "name": o.get("surname", "") + o.get("given", ""),
            "rank": o.get("rank_name", ""),
            "province": pname,
            "out_file": "full_%04d.png" % o["id"],
            "prompt": build_prompt(o, pname),
        })

    result = {
        "count": len(items),
        "style": "和风写实 HD-2D",
        "image_size": "1024x1536",
        "background": "transparent",
        "negative": NEGATIVE,
        "usage": "逐条调用 ImageGen(prompt=item['prompt'], size='1024x1536', background='transparent')；"
                 "产出另存为 assets/gfx/portrait/full_{id:04d}.png",
        "items": items,
    }

    out_path = args.out or os.path.join(OUT_DIR, "portrait_prompts.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

    print("=== HD-2D 立绘提示词生成 ===")
    print("  武将数  : %d" % len(items))
    print("  输出    : %s" % out_path)
    print("  图片规格: 1024x1536，透明背景")
    print()
    for it in items[:5]:
        print("  #%d %s（%s）" % (it["id"], it["name"], it["rank"]))
        print("     %s" % it["prompt"][:150] + "...")
    if len(items) > 5:
        print("  ... 其余 %d 条见 JSON" % (len(items) - 5))

    if args.csv:
        csv_path = out_path.replace(".json", ".csv")
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "name", "rank", "province", "out_file", "prompt"])
            for it in items:
                w.writerow([it["id"], it["name"], it["rank"], it["province"],
                            it["out_file"], it["prompt"]])
        print("\n  CSV 已导出: %s" % csv_path)


if __name__ == "__main__":
    main()
