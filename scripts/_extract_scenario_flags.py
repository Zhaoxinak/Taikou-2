"""Export SNDATA castle-code flag snapshot for scenario 1/2."""
import json
import os
import struct

DATA = r"F:\Games\Taikou2"
OUT = os.path.join(os.path.dirname(__file__), "scenario_castle_flags.json")
CASTLE_MAX = 0xC8  # 200 castle codes 0x00-0xC7


def read_flags(path: str) -> bytes:
    raw = open(path, "rb").read()
    return raw[20:]


def main() -> None:
    f1 = read_flags(os.path.join(DATA, "SNDATA1.TR2"))
    f2 = read_flags(os.path.join(DATA, "SNDATA2.TR2"))
    castles = []
    for cid in range(CASTLE_MAX):
        castles.append(
            {
                "id": cid,
                "code_hex": f"0x{cid:02X}",
                "scenario1": int(f1[cid]) if cid < len(f1) else 0,
                "scenario2": int(f2[cid]) if cid < len(f2) else 0,
            }
        )
    s1_ones = sum(1 for c in castles if c["scenario1"] == 1)
    s2_ones = sum(1 for c in castles if c["scenario2"] == 1)
    out = {
        "note": "SNDATA flag byte at index == castle code (0x00-0xC7); hypothesis, 90/200 ones in scenario1",
        "castle_count": CASTLE_MAX,
        "scenario1_ones_under_200": s1_ones,
        "scenario2_ones_under_200": s2_ones,
        "castles": castles,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"wrote {OUT} s1={s1_ones} s2={s2_ones}")


if __name__ == "__main__":
    main()
