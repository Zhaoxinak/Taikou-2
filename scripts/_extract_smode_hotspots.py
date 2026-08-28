"""Extract SMODE.GRP scenario click rects (heuristic from pixel layout)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _graph_probe import decode_rgb565  # noqa: E402

DATA = r"F:\Games\Taikou2"
OUT = os.path.join(os.path.dirname(__file__), "smode_hotspots.json")
W, H = 320, 200


def find_split_x(rgb: list[int]) -> int:
    var = []
    for x in range(W):
        s = sum(rgb[(y * W + x) * 3] + rgb[(y * W + x) * 3 + 1] + rgb[(y * W + x) * 3 + 2] for y in range(40, 180))
        var.append(s)
    return min(range(80, 240), key=lambda x: var[x])


def main() -> None:
    raw = open(os.path.join(DATA, "SMODE.GRP"), "rb").read()
    rgb = decode_rgb565(raw[: W * H * 2])
    split = find_split_x(rgb)
    out = {
        "note": "SMODE.GRP 320x200 hotspots; split_x from pixel valley; tail 5537B TBD",
        "width": W,
        "height": H,
        "split_x": split,
        "scenarios": [
            {"id": 1, "label": "剧本一（尾张·入门）", "rect": [20, 70, split - 10, 170]},
            {"id": 2, "label": "剧本二（近江·进阶）", "rect": [split + 10, 70, 300, 170]},
        ],
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"wrote {OUT} split_x={split}")


if __name__ == "__main__":
    main()
