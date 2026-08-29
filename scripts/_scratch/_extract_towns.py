#!/usr/bin/env python3
"""从 TOWNPOS.DAT + castle_names.json 生成 scripts/towns.json。"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get("TAIKOU_DATA", r"F:\Games\Taikou2")
OUT = os.path.join(ROOT, "scripts", "towns.json")
CASTLE_FILE = os.path.join(ROOT, "scripts", "castle_names.json")

# 剧情锚点：键 = 居城代码（与 TOWNPOS 行号、bsdata home_city 一致）
# (显示名覆盖, enemy, desc) — 显示名留空则用城名表
STORY: dict[int, tuple[str, str, str]] = {
    0x42: ("", "", "尾张要冲，清洲城。织田家的据点，你可在此安心修行。"),  # 清洲
    0x47: ("那古野城", "", "尾张的南大门，通往天下的起点。"),  # 那古野
    0x48: ("岐阜城", "saito", "美浓要冲，斋藤龙兴据守（稻叶山）。"),
    0x60: ("小谷城", "asai", "近江名城，浅井家据守。"),  # 小谷
    0x70: ("二条城", "nobunaga", "京城心脏，织田信长坐镇于此（朽木谷位点代用，二条无 TOWNPOS）。"),
}


def load_castle_names() -> dict[int, str]:
    data = json.load(open(CASTLE_FILE, encoding="utf-8"))
    out: dict[int, str] = {}
    for c in data["castles"]:
        out[int(c["id"])] = c["display"]
    return out


def town_pos(row: bytes) -> tuple[int, int] | None:
    valid = []
    for i in range(0, 16, 2):
        x, y = row[i], row[i + 1]
        if 0 < x < 180 and 0 < y < 88:
            valid.append((x, y))
    if not valid:
        return None
    # 多坐标行取最北（y 最小）的点，更符合地图主据点。
    return min(valid, key=lambda p: (p[1], p[0]))


def castle_label(code: int, names: dict[int, str]) -> str:
    return names.get(code, f"城{code}")


def main() -> None:
    pos = open(os.path.join(DATA, "TOWNPOS.DAT"), "rb").read()
    names = load_castle_names()

    towns = []
    for r in range(len(pos) // 16):
        p = town_pos(pos[r * 16 : r * 16 + 16])
        if not p:
            continue
        x, y = p
        base_name = castle_label(r, names)
        if r in STORY:
            override, enemy, desc = STORY[r]
            name = override if override else base_name
        else:
            name, enemy, desc = base_name, "", f"{base_name}，居城代码 0x{r:02X}。"
        towns.append({
            "id": r,
            "code_hex": f"{r:02X}",
            "name": name,
            "map_x": x,
            "map_y": y,
            "x": round(x / 256, 4),
            "y": round(y / 88, 4),
            "enemy": enemy,
            "desc": desc,
        })

    out = {
        "count": len(towns),
        "source": "TOWNPOS.DAT + castle_names.json",
        "towns": towns,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"OK {len(towns)} towns -> {OUT}")
    for code in STORY:
        hit = next((t for t in towns if t["id"] == code), None)
        if hit:
            print(f"  STORY 0x{code:02X} {hit['name']} enemy={hit['enemy'] or '-'} @ ({hit['map_x']},{hit['map_y']})")
        else:
            print(f"  STORY 0x{code:02X} MISSING (no TOWNPOS coords)")


if __name__ == "__main__":
    main()
