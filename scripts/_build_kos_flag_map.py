"""Scan KOS bytecode for uint16 refs in SNDATA story range (200-399) → kos_story_flag_map.json"""
import json
import os
import struct

DATA = r"F:\Games\Taikou2"
OUT = os.path.join(os.path.dirname(__file__), "kos_story_flag_map.json")
KEY = 0xAE
HDR = 20
STORY_MIN = 200
STORY_MAX = 400


def decrypt_kos(path: str) -> bytes:
    return bytes(b ^ KEY for b in open(path, "rb").read()[HDR:])


def story_flags_set(scenario: int) -> set[int]:
    raw = open(os.path.join(DATA, f"SNDATA{scenario}.TR2"), "rb").read()
    flags = raw[20:]
    return {i for i in range(STORY_MIN, STORY_MAX) if i < len(flags) and flags[i] == 1}


def scan_kos(kos: str, s1_set: set[int]) -> dict:
    path = os.path.join(DATA, kos)
    dec = decrypt_kos(path)
    blob = dec[dec.find(b"data") + 8 :] if b"data" in dec else dec
    hits: set[int] = set()
    for off in range(0, len(blob) - 2, 2):
        v = struct.unpack_from("<H", blob, off)[0]
        if v in s1_set:
            hits.add(v)
    return sorted(hits)


def main() -> None:
    s1_set = story_flags_set(1)
    kos_files = sorted(f for f in os.listdir(DATA) if f.upper().endswith(".KOS"))
    events: dict[str, dict] = {}
    for idx, kos in enumerate(kos_files):
        flags = scan_kos(kos, s1_set)
        slot = STORY_MIN + idx
        events[kos] = {
            "kos_index": idx,
            "hypothesis_flag": slot,
            "bytecode_flags": flags,
        }
    out = {
        "note": "bytecode_flags = uint16 in KOS body that match SNDATA1 story indices 200-399 with value 1",
        "story_range": [STORY_MIN, STORY_MAX - 1],
        "events": events,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    mapped = sum(1 for e in events.values() if e["bytecode_flags"])
    print(f"mapped {mapped}/{len(kos_files)} kos with story flags -> {OUT}")


if __name__ == "__main__":
    main()
