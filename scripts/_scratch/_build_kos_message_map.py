"""Scan KOS bytecode for MESSAGE uint16 refs → kos_message_map.json"""
import json
import os
import struct
import sys

DATA = r"F:\Games\Taikou2"
OUT = os.path.join(os.path.dirname(__file__), "kos_message_map.json")
sys.path.insert(0, os.path.dirname(__file__))
from _graph_probe import ls11  # noqa: E402

KEY = 0xAE
HDR = 20

# 无 MESSAGE 引用的 UI/音效脚本，或人工校对条目
MANUAL_OVERRIDES: dict[str, int] = {
    "TEPPOU.KOS": 14,
    "MI_AME.KOS": 1327,
    "SHIPPAI.KOS": 1732,
    "GIHEI.KOS": 596,
    "METUBUSI.KOS": 959,
}
UI_ONLY = {"CANCEL.KOS", "CLICK.KOS"}


def load_msgs() -> list[bytes]:
    msgs: list[bytes] = []
    for n in range(1, 5):
        path = os.path.join(DATA, f"MESSAGE{n}.LZW")
        if not os.path.exists(path):
            continue
        d = ls11(open(path, "rb").read())
        cnt = struct.unpack_from("<H", d, 4)[0]
        ptrs = [struct.unpack_from("<I", d, 6 + i * 4)[0] for i in range(cnt)]
        for i in range(cnt):
            s = ptrs[i]
            e = ptrs[i + 1] if i + 1 < cnt else len(d)
            msgs.append(d[s:e])
    return msgs


def dec_msg(raw: bytes) -> str:
    out: list[str] = []
    i = 0
    while i < len(raw):
        if raw[i] == 0:
            break
        if raw[i] < 0x80:
            out.append(chr(raw[i]))
            i += 1
        elif i + 1 < len(raw):
            try:
                out.append(raw[i : i + 2].decode("gbk"))
            except UnicodeDecodeError:
                pass
            i += 2
        else:
            break
    return "".join(out)


def best_msg_id(kos: str, msgs: list[bytes], relaxed: bool = False) -> int | None:
    path = os.path.join(DATA, kos)
    if not os.path.exists(path):
        return None
    dec = bytes(b ^ KEY for b in open(path, "rb").read()[HDR:])
    doff = dec.find(b"data")
    blob = dec[doff + 8 :] if doff >= 0 else dec
    hits: dict[int, int] = {}
    for off in range(len(blob) - 2):
        v = struct.unpack_from("<H", blob, off)[0]
        if v >= len(msgs):
            continue
        t = dec_msg(msgs[v])
        han = sum(1 for c in t if "\u4e00" <= c <= "\u9fff")
        min_han = 2 if relaxed else 4
        min_len = 4 if relaxed else 8
        if han < min_han or len(t) < min_len or len(t) > 200:
            continue
        hits[v] = hits.get(v, 0) + 1
    if not hits:
        return None
    return max(hits.items(), key=lambda x: (x[1], -x[0]))[0]


def main() -> None:
    msgs = load_msgs()
    kos_files = sorted(f for f in os.listdir(DATA) if f.upper().endswith(".KOS"))
    events: dict[str, dict] = {}
    for kos in kos_files:
        if kos in UI_ONLY:
            events[kos] = {"msg_id": -1, "text": "", "ui_only": True}
            continue
        mid = MANUAL_OVERRIDES.get(kos)
        if mid is None:
            mid = best_msg_id(kos, msgs, relaxed=False)
        if mid is None:
            mid = best_msg_id(kos, msgs, relaxed=True)
        if mid is not None:
            events[kos] = {"msg_id": mid, "text": dec_msg(msgs[mid])}
    out = {
        "note": "MESSAGE global index from KOS bytecode uint16 scan",
        "message_count": len(msgs),
        "events": events,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"mapped {len(events)} / {len(kos_files)} -> {OUT}")


if __name__ == "__main__":
    main()
