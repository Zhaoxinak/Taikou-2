# -*- coding: utf-8 -*-
"""
gen_portrait_prompts.py — 生成 695 张武将立绘的提示词与「生成台账」
=================================================================
用途
----
按 tools/portrait_prompts.json 确立的风格模板，为全部真实武将（695 名）
逐条拼出 ImageGen 提示词，并产出可断点续跑的台账 tools/portrait_ledger.json。

台账是**跨会话/换 AI 续跑的唯一真源**：
  每次跑本脚本都会扫 assets/sprites/portraits/，已存在的真图自动标记 done，
  不会重复生成、不会重复烧积分。

关键数据修正（务必保留）
------------------------
1. 输出文件名是 **{id}.png**（不是 full_0013.png）——
   src/render/asset_loader.gd 实际按 "res://assets/sprites/portraits/%d.png" 加载。
   tools/portrait_prompts.json 里写的 assets/gfx/portrait/full_XXXX.png 已过时。
2. 尺寸按 src/render/AssetSpec.gd: PORTRAIT_SIZE = 512×640（4:5）。
   生成用 1024×1280（2x），再用 Pillow 缩到 512×640 落盘。
3. 国名不能直接用 officer["province"] —— 该字段与国表索引**对不上**
   （织田信长 province=13 会解成骏河，实为尾张）。
   正解：officer["city"] → castles[city]["province"] → provinces[idx]["name"]。

用法
----
    python tools/gen_portrait_prompts.py              # 生成/刷新台账
    python tools/gen_portrait_prompts.py --top 20     # 只看优先级最高的 20 条
"""
import argparse
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_LEDGER = os.path.join(ROOT, "tools", "portrait_ledger.json")
PORTRAIT_DIR = os.path.join(ROOT, "assets", "sprites", "portraits")

GEN_SIZE = "1024x1280"     # 2x
FINAL_SIZE = (512, 640)    # AssetSpec.PORTRAIT_SIZE (4:5)
BACKGROUND = "transparent"
STYLE = "和风写实 HD-2D"
NEGATIVE = ("blurry, photorealistic, 3D render, western armor, modern clothing, "
            "smooth gradients, anti-aliased pixels, low resolution, jpeg artifacts, "
            "watermark, text, multiple characters")

START_YEAR = 1560

# 職位 → 英文描述（与 portrait_prompts.json 样例保持一致）
RANK_DESC = {
    "大名": "daimyo warlord, elaborate armor with gold accents",
    "家老": "karou elder retainer, formal court armor",
    "家臣": "household retainer, formal court armor",
    "组头": "kumi-gashira captain, officer armor",
    "足轻头": "ashigaru head, light lacquer armor",
    "足轻组头": "ashigaru squad leader, light lacquer armor",
    "足轻工头": "ashigaru engineer, practical work armor",
    "无": "ronin masterless samurai, worn traveling armor",
}

# 知名武将的固定人设（archetype_name 精确匹配）
FAMOUS_TRAITS = {
    "织田信长": "ambitious conqueror, commanding aura",
    "上杉谦信": "pious warlord, devout expression",
    "本愿寺显如": "pious warlord, devout expression",
    "柴田胜家": "veteran warrior, blunt honest face, heavy build",
    "木下藤吉郎": "humble origin, clever sharp eyes, thin build",
    "明智光秀": "refined intelligent features, composed",
}

TAIL = ("Octopath Traveler HD-2D aesthetic, soft rim lighting, warm amber color palette, "
        "detailed armor texture and fabric folds, sharp clean pixel edges, "
        "dramatic cinematic lighting, game character portrait")

# v2 统一风格段（2026-09-10 风格审查后固化）：
#   - 禁止铠甲/背景文字（此前 "clan of X" 被模型画成画面文字）
#   - 统一暖黄虚化渐变背景，避免偏冷/暗部具象化背景
#   - 刻意不加 bright well-lit / vivid saturated（实测会导致画面过亮过艳、与主流脱节）
STYLE_FIX = (" and warm amber gradient background, soft out-of-focus bokeh glow, "
             "no text, no kanji, no letters on armor or background")


def load():
    officers = json.load(open(os.path.join(ROOT, "data", "officers.json"), encoding="utf-8"))
    castles = json.load(open(os.path.join(ROOT, "data", "castles.json"), encoding="utf-8"))["castles"]
    provinces = json.load(open(os.path.join(ROOT, "data", "provinces.json"), encoding="utf-8"))["provinces"]
    return officers, castles, provinces


def province_name(o, castles, provinces):
    """officer.city → castles[city].province → provinces[idx].name
    ⚠️ officer['province'] 与国表索引对不上，勿直接用。"""
    city = o.get("city")
    if isinstance(city, int) and 0 <= city < len(castles):
        pi = castles[city].get("province")
        if isinstance(pi, int) and 0 <= pi < len(provinces):
            return provinces[pi].get("name") or "日本"
    return "日本"


def age_desc(o):
    by = o.get("birth_year")
    age = START_YEAR - by if isinstance(by, int) and by > 1000 else 30
    if not (14 <= age <= 80):
        age = 30
    if age < 20:
        return f"youthful, about {age} years old"
    if age <= 35:
        return f"in his prime, about {age} years old"
    if age <= 52:
        return f"middle-aged, about {age} years old"
    return f"elderly, about {age} years old"


def trait_desc(o):
    full = (o.get("surname", "") + o.get("given", ""))
    if full in FAMOUS_TRAITS:
        return FAMOUS_TRAITS[full]
    f = o.get("forces") or {}
    lead = f.get("lead", 0)
    martial = f.get("martial", 0)
    domestic = f.get("domestic", 0)
    diplomacy = f.get("diplomacy", 0)
    charm = f.get("charm", 0)
    parts = []
    if martial >= 85:
        parts.append("battle-worn armor, fierce expression, scars")
    elif martial >= 70:
        parts.append("seasoned warrior look, hardened gaze")
    if lead >= 80:
        parts.append("natural leader bearing, commanding presence, authoritative posture")
    if charm >= 80:
        parts.append("refined noble features, charismatic smile")
    if domestic >= 80:
        parts.append("scholarly air, court attire accents")
    if diplomacy >= 80:
        parts.append("composed diplomat, elegant manner")
    if not parts:
        parts.append("steadfast retainer, calm demeanor")
    return ", ".join(parts)


def build_prompt(o, castles, provinces):
    rank = RANK_DESC.get(o.get("rank_name") or "", "samurai retainer, serviceable armor")
    return (f"HD-2D style portrait, Japanese Sengoku warlord, half-body, "
            f"4:5 vertical composition, high-resolution pixel art with realistic "
            f"Japanese aesthetics, {age_desc(o)}, {rank}, "
            f"{trait_desc(o)}, {TAIL}{STYLE_FIX}")


def tier_of(o):
    """生成优先级：1=可选主角 2=知名武将 3=大名 4=其余"""
    if o.get("is_selectable"):
        return 1
    arch = o.get("archetype_name") or ""
    if arch and not arch.startswith("一般"):
        return 2
    if (o.get("rank_name") or "") == "大名":
        return 3
    return 4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=0, help="只看优先级最高的 N 条")
    args = ap.parse_args()

    officers, castles, provinces = load()
    real = [o for o in officers if not o.get("is_placeholder")]

    items = []
    for o in real:
        oid = int(o["id"])
        name = o.get("surname", "") + o.get("given", "")
        # 新命名规则：{id}_{姓名}.png（无后缀是默认；多张候选时为 {id}_{姓名}-N.png）
        # done 检测同时认主名和 -N 后缀（旧式纯 {id}.png 不再视为已生成 → 需走 finalize 重命名）
        primary = f"{oid}_{name}.png"
        candidates = [primary] + [f"{oid}_{name}-{i}.png" for i in range(1, 10)]
        exists = any(os.path.exists(os.path.join(PORTRAIT_DIR, c)) for c in candidates)
        items.append({
            "id": oid,
            "name": name,
            "rank": o.get("rank_name") or "",
            "province": province_name(o, castles, provinces),
            "tier": tier_of(o),
            "prompt": build_prompt(o, castles, provinces),
            "out_file": primary,
            "status": "done" if exists else "pending",
        })

    items.sort(key=lambda x: (x["tier"], x["id"]))

    done = sum(1 for i in items if i["status"] == "done")
    ledger = {
        "meta": {
            "style": STYLE,
            "gen_size": GEN_SIZE,
            "final_size": list(FINAL_SIZE),
            "background": BACKGROUND,
            "negative": NEGATIVE,
            "out_dir": "assets/sprites/portraits/",
            "loader": "res://assets/sprites/portraits/{id}.png (src/render/asset_loader.gd)",
            "total": len(items),
            "done": done,
            "pending": len(items) - done,
            "note": ("文件名是 {id}.png 不是 full_XXXX.png；"
                     "国名走 city→castle.province，勿用 officer.province"),
        },
        "items": items,
    }
    json.dump(ledger, open(OUT_LEDGER, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print(f"[gen_portrait_prompts] 台账写入 {OUT_LEDGER}")
    print(f"  总武将 {len(items)}  已生成 {done}  待生成 {len(items) - done}")
    for t in (1, 2, 3, 4):
        n = sum(1 for i in items if i["tier"] == t)
        print(f"  tier{t}: {n}")
    if args.top:
        print(f"\n== 优先级最高 {args.top} 条 ==")
        for i in items[:args.top]:
            print(f"  [{i['id']:>3}] {i['name']:<8} {i['rank']:<5} {i['province']:<5} {i['status']}")


if __name__ == "__main__":
    main()
