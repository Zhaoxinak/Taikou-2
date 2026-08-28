"""Build kos_opcodes.json from MESSAGE-ref context bytes."""
import json
import os
import struct
from collections import Counter

DATA = r"F:\Games\Taikou2"
OUT = os.path.join(os.path.dirname(__file__), "kos_opcodes.json")
KEY = 0xAE
HDR = 20

GUESSES = {
    9: "show_message",
    10: "show_message",
    16: "show_message",
    21: "show_message",
    29: "show_message",
    41: "show_message",
    76: "show_message",
    107: "branch",
    1: "noop",
}


def main() -> None:
    msg_map = json.load(open(os.path.join(os.path.dirname(__file__), "kos_message_map.json"), encoding="utf-8"))[
        "events"
    ]
    single: Counter[int] = Counter()
    pair: Counter[tuple[int, int]] = Counter()
    samples: dict[str, list[dict]] = {}

    for kos, ent in msg_map.items():
        if ent.get("ui_only"):
            continue
        mid = ent.get("msg_id", -1)
        if mid < 0:
            continue
        path = os.path.join(DATA, kos)
        if not os.path.exists(path):
            continue
        dec = bytes(b ^ KEY for b in open(path, "rb").read()[HDR:])
        blob = dec[dec.find(b"data") + 8 :]
        pos = blob.find(struct.pack("<H", mid))
        if pos < 1:
            continue
        b1 = blob[pos - 1]
        single[b1] += 1
        if pos >= 2:
            b0 = blob[pos - 2]
            pair[(b0, b1)] += 1
            samples.setdefault(kos, []).append({"offset": pos, "b0": b0, "b1": b1, "msg_id": mid})

    opcodes = {}
    for byte, count in single.items():
        opcodes[str(byte)] = {
            "count": count,
            "guess": GUESSES.get(byte, "unknown"),
        }
    out = {
        "note": "Single byte immediately before mapped MESSAGE uint16 in KOS bytecode",
        "opcodes": opcodes,
        "top_pairs": [
            {"b0": a, "b1": b, "count": c} for (a, b), c in pair.most_common(12)
        ],
        "samples": {k: v[:2] for k, v in list(samples.items())[:8]},
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"wrote {OUT} opcodes={len(opcodes)}")


if __name__ == "__main__":
    main()
