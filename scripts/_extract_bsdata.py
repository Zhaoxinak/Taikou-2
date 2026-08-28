#!/usr/bin/env python3
"""从 BSDATA1.TR2 生成 scripts/bsdata.json（中文汉化版 59 字节/条）。"""
import json
import os
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get("TAIKOU_DATA", r"F:\Games\Taikou2")
OUT = os.path.join(ROOT, "scripts", "bsdata.json")
RECORD_SIZE = 59
COUNT = 700

SKILL_NAMES = [
    "算用", "剑术", "口才", "马术", "洋枪",
    "筑城", "忍术", "军学", "礼法", "茶道",
]
FORCE_NAMES = ["统率", "武力", "内政", "外交", "魅力"]

STATUS_NAMES = {
    0: "无",
    1: "足轻组头",
    2: "足轻工头",
    3: "足轻头",
    4: "家老",
    5: "组头",
    6: "家臣",
    7: "大名",
}


def gbk_name(chunk: bytes, start: int, end: int) -> str:
    raw = chunk[start:end].split(b"\x00", 1)[0]
    return raw.decode("gbk", errors="replace").strip()


def decode_skills(b27: int, b28: int, b29: int) -> dict[str, int]:
    nibbles = [
        (b27 >> 4) & 0xF,
        b27 & 0xF,
        (b28 >> 4) & 0xF,
        b28 & 0xF,
        b29 & 0xF,
    ]
    out: dict[str, int] = {}
    for i, v in enumerate(nibbles):
        out[SKILL_NAMES[i * 2]] = v & 3
        out[SKILL_NAMES[i * 2 + 1]] = (v >> 2) & 3
    return out


def decode_record(rec: bytes, cid: int) -> dict:
    name = gbk_name(rec, 0, 4) + gbk_name(rec, 7, 13)
    face = rec[16]
    compat = rec[20]
    forces = {FORCE_NAMES[i]: rec[22 + i] for i in range(5)}
    skills = decode_skills(rec[27], rec[28], rec[29])
    trust = rec[50] | (rec[51] << 8)
    return {
        "id": cid,
        "name": name,
        "forces": forces,
        "skills": skills,
        "face": face,
        "compat": compat,
        "age_code": rec[43],
        "stamina_max": rec[45],
        "stamina": rec[46],
        "ambition": rec[47],
        "intimacy": rec[48],
        "home_city": rec[49],
        "trust": trust,
        "salary": rec[52],
        "loyalty": rec[56],
        "status": rec[57],
        "status_name": STATUS_NAMES.get(rec[57], f"身份{rec[57]}"),
        "lifespan": rec[58],
    }


def main() -> None:
    path = os.path.join(DATA, "BSDATA1.TR2")
    raw = open(path, "rb").read()
    assert len(raw) == RECORD_SIZE * COUNT, f"unexpected size {len(raw)}"

    chars = []
    for cid in range(COUNT):
        rec = raw[cid * RECORD_SIZE : (cid + 1) * RECORD_SIZE]
        chars.append(decode_record(rec, cid))

    out = {
        "record_size": RECORD_SIZE,
        "count": COUNT,
        "fields": (
            "name@0-12 face@16 compat@20 abilities@22-26 skills@27-29 "
            "age_code@43 stamina_max@45 stamina@46 ambition@47 intimacy@48 "
            "home_city@49 trust@50-51 salary@52 loyalty@56 status@57 lifespan@58"
        ),
        "status_note": "status 映射见 STATUS_NAMES；age_code 为游戏内部年龄编码（非直接岁数）",
        "characters": chars,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # spot checks
    by_id = {c["id"]: c for c in chars}
    oda = by_id[13]
    hide = by_id[16]
    keiji = by_id[27]
    assert oda["name"] == "织田信长" and oda["forces"]["统率"] == 96
    assert hide["name"] == "木下藤吉郎" and hide["forces"]["武力"] == 42
    assert keiji["skills"]["剑术"] == 3, keiji["skills"]
    print(f"OK {len(chars)} characters -> {OUT}")
    print(
        f"  #13 {oda['name']} 野{oda['ambition']} 忠{oda['loyalty']} 寿{oda['lifespan']}"
    )
    print(
        f"  #16 {hide['name']} 体{hide['stamina']}/{hide['stamina_max']} 俸{hide['salary']}"
    )


if __name__ == "__main__":
    main()
