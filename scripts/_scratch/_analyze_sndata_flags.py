"""Analyze SNDATA flag regions and export scenario_flag_regions.json."""
import json
import os

DATA = r"F:\Games\Taikou2"
OUT = os.path.join(os.path.dirname(__file__), "scenario_flag_regions.json")
MAGIC_SIZE = 16
CASTLE_END = 200
STORY_BASE = 200
STORY_END = 4000


def read_flags(path: str) -> bytes:
    return open(path, "rb").read()[MAGIC_SIZE + 4 :]


def ones_in(flags: bytes, start: int, end: int) -> list[int]:
    return [i for i in range(start, min(end, len(flags))) if flags[i] == 1]


def main() -> None:
    f1 = read_flags(os.path.join(DATA, "SNDATA1.TR2"))
    f2 = read_flags(os.path.join(DATA, "SNDATA2.TR2"))
    o1 = set(i for i, b in enumerate(f1) if b == 1)
    o2 = set(i for i, b in enumerate(f2) if b == 1)
    s1_only = sorted(o1 - o2)
    s2_only = sorted(o2 - o1)
    both = sorted(o1 & o2)

    castle_s1 = ones_in(f1, 0, CASTLE_END)
    castle_s2 = ones_in(f2, 0, CASTLE_END)
    story_s1 = ones_in(f1, STORY_BASE, STORY_END)
    story_s2 = ones_in(f2, STORY_BASE, STORY_END)

    # Hypothesis: story slot 200+castle_id mirrors active castle (57/90 in scenario 1).
    mirror_hits = sum(
        1 for cid in castle_s1 if (STORY_BASE + cid) < len(f1) and f1[STORY_BASE + cid] == 1
    )

    ext_regions = []
    for start, end, name in [(400, 799, "extended_a"), (800, 1599, "extended_b"), (1600, 3999, "extended_c")]:
        ext_regions.append({
            "name": name,
            "start": start,
            "end": end,
            "scenario1_ones": sum(1 for i in ones_in(f1, start, end + 1)),
            "scenario2_ones": sum(1 for i in ones_in(f2, start, end + 1)),
        })

    out = {
        "note": "SNDATA flag area after 16B magic + 4B seed. Index 0-199=castle codes (verified). 200+=story/event slots (hypothesis).",
        "flag_size": len(f1),
        "regions": [
            {"name": "castle", "start": 0, "end": CASTLE_END - 1, "scenario1_ones": len(castle_s1), "scenario2_ones": len(castle_s2)},
            {"name": "story", "start": STORY_BASE, "end": STORY_END - 1, "scenario1_ones": len(story_s1), "scenario2_ones": len(story_s2)},
        ],
        "scenario1_total_ones": len(o1),
        "scenario2_total_ones": len(o2),
        "both_scenarios_ones": len(both),
        "scenario1_only_count": len(s1_only),
        "scenario2_only_count": len(s2_only),
        "scenario1_only_sample": s1_only[:30],
        "scenario2_only_sample": s2_only[:30],
        "castle_story_mirror_hits_s1": mirror_hits,
        "castle_story_mirror_total_s1": len(castle_s1),
        "extended_regions": ext_regions,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"wrote {OUT} mirror={mirror_hits}/{len(castle_s1)}")


if __name__ == "__main__":
    main()
