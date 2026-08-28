"""Export kos_effect_map.json from KosEvents effects + bytecode skill hints."""
import json
import os
import struct

DATA = r"F:\Games\Taikou2"
OUT = os.path.join(os.path.dirname(__file__), "kos_effect_map.json")
KEY = 0xAE
HDR = 20

SKILLS = ["算用", "剑术", "口才", "马术", "洋枪", "筑城", "忍术", "军学", "礼法", "茶道"]

# Mirror of KosEvents.EVENTS effect fields (kos -> effects without title/text/weight/scenarios)
MANUAL: dict[str, dict] = {
    "MACHIMES.KOS": {"money": [5, 25], "charm": [0, 1]},
    "GINOUUP.KOS": {"skill_up": 1},
    "KAKEI.KOS": {"money": [-30, -5]},
    "KOATARI.KOS": {"money": [10, 40]},
    "OOATARI.KOS": {"money": [50, 120]},
    "KAMINARI.KOS": {"hp": [-15, -5]},
    "MI_AME.KOS": {"charm": [1, 2]},
    "MI_HARE.KOS": {"hp": [5, 15]},
    "NINJA.KOS": {"might": [1, 2], "hp": [-8, -2]},
    "TEPPOU.KOS": {"skill": "洋枪"},
    "KEMURI.KOS": {"hp": [8, 20]},
    "SEIKOU.KOS": {"lead": [1, 2]},
    "SHIPPAI.KOS": {"money": [-20, -8], "charm": [-1, 0]},
    "SYUUZEN.KOS": {"politics": [1, 2], "money": [0, 15]},
    "GIHEI.KOS": {"might": [1, 1], "lead": [1, 1]},
    "TOTUGEKI.KOS": {"skill": "马术"},
    "ZANSYU.KOS": {"lead": [1, 2], "skill": "忍术"},
    "SHIKI.KOS": {"charm": [1, 2], "politics": [1, 1]},
    "IKARI.KOS": {"lead": [1, 2], "ambition_stat": [1, 2]},
    "MATISIRO.KOS": {"politics": [1, 2], "money": [0, 20]},
}


def bytecode_skill_hint(kos: str, msg_id: int) -> str | None:
    path = os.path.join(DATA, kos)
    if not os.path.exists(path) or msg_id < 0:
        return None
    dec = bytes(b ^ KEY for b in open(path, "rb").read()[HDR:])
    blob = dec[dec.find(b"data") + 8 :] if b"data" in dec else dec
    pos = blob.find(struct.pack("<H", msg_id))
    if pos < 0:
        return None
    window = blob[max(0, pos - 16) : pos]
    idxs = [b for b in window if b < len(SKILLS)]
    if len(idxs) == 1:
        return SKILLS[idxs[0]]
    return None


def main() -> None:
    msg_map = json.load(open(os.path.join(os.path.dirname(__file__), "kos_message_map.json"), encoding="utf-8"))[
        "events"
    ]
    events: dict[str, dict] = {}
    for kos, fx in MANUAL.items():
        entry = dict(fx)
        mid = msg_map.get(kos, {}).get("msg_id", -1)
        hint = bytecode_skill_hint(kos, mid)
        if hint and "skill" not in entry and "skill_up" not in entry:
            entry["skill_hint"] = hint
            entry["skill"] = hint
        events[kos] = entry
    out = {
        "note": "KOS event stat effects; skill_hint from bytecode uint8 before MESSAGE ref",
        "skills": SKILLS,
        "events": events,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"wrote {OUT} {len(events)} entries")


if __name__ == "__main__":
    main()
