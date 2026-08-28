#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""49 国国情表 PROVINCE_STATE @0x519548 — 可执行参考 + 自检。

来源：SNDATA XOR 解密流（填充器 0x47e3a0），流偏移 27052。
布局（5B/国）：+0 size_tier | +1 climate | +2 flags | +3..+4 u16(yield_hi5|map_band)
"""
from __future__ import annotations

import json
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, "province_spec.json")
DATA_CANDIDATES = [
    os.path.join(HERE, "..", "Taikou2 Original"),
    r"F:/Games/Taikou2",
]

STREAM_OFF = 27052  # 22 + 59*370 + 26*200
SNOW_GROUPS = frozenset((0, 2, 4))


def _data_root() -> str:
    for p in DATA_CANDIDATES:
        if os.path.isfile(os.path.join(p, "SNDATA1.TR2")):
            return p
    raise FileNotFoundError("SNDATA1.TR2 not found")


def decrypt_stream(path: str) -> tuple[bytes, int]:
    raw = open(path, "rb").read()
    assert raw[:16] == b"TAIKOU2_SCENARIO"
    key = raw[0x12] ^ raw[0x13]
    stream = bytearray(raw[0x598:])
    for i in range(len(stream)):
        stream[i] ^= key
    return bytes(stream), key


def parse_province_block(block: bytes) -> list[dict]:
    assert len(block) >= 245
    out = []
    for i in range(49):
        b = block[i * 5 : (i + 1) * 5]
        u16 = struct.unpack_from("<H", b, 3)[0]
        out.append(
            {
                "id": i,
                "size_tier": b[0] & 0x0F,
                "byte0_hi2": (b[0] >> 4) & 3,
                "climate_group": b[1],
                "is_snow_region": b[1] in SNOW_GROUPS,
                "flags": b[2],
                "flag_0x40": bool(b[2] & 0x40),
                "yield_lo2": u16 & 3,
                "yield_hi5": (u16 >> 2) & 0x1F,
                "map_band": (u16 >> 8) & 0xFF,
            }
        )
    return out


def load_scenario(which: int = 1) -> list[dict]:
    root = _data_root()
    path = os.path.join(root, f"SNDATA{which}.TR2")
    stream, _ = decrypt_stream(path)
    return parse_province_block(stream[STREAM_OFF : STREAM_OFF + 245])


def set_yield_hi5(u16: int, val: int) -> int:
    """Mirror 0x49b280: clamp val≤0x1d, pack into bits2..6, keep lo2 + hi8."""
    val = min(max(val, 0), 0x1D)
    return (u16 & 0xFF83) | ((val & 0x1F) << 2)


def monthly_yield_tick(hi5: int, r1: int, r2: int) -> int:
    """Mirror 0x4a59d0 read-side clamp before 0x49b280 write.
    r1,r2 = rand()%10 each; avg=(hi5+r1+r2)//2; clamp to [6,22].
    """
    v = (hi5 + (r1 & 0xFFFF) + (r2 & 0xFFFF)) // 2
    return max(6, min(22, v & 0xFFFF))


def selfcheck() -> None:
    spec = json.load(open(SPEC, encoding="utf-8"))
    recs = load_scenario(1)
    assert len(recs) == 49
    assert STREAM_OFF == spec["stream_offset"]
    # 北陆奥 snow, 房总 warm
    assert recs[0]["is_snow_region"] and recs[0]["climate_group"] == 0
    assert not recs[7]["is_snow_region"] and recs[7]["climate_group"] == 1
    # map_band north→south non-decreasing for 0..43
    bands = [r["map_band"] for r in recs[:44]]
    assert bands == sorted(bands), bands
    # yield setter roundtrip
    assert set_yield_hi5(0x011C, 7) == ((0x011C & 0xFF83) | (7 << 2))
    assert monthly_yield_tick(7, 3, 5) == 7  # (7+3+5)//2=7
    assert monthly_yield_tick(0, 0, 0) == 6
    assert monthly_yield_tick(30, 9, 9) == 22
    snow = [r["id"] for r in recs if r["is_snow_region"]]
    assert len(snow) == len(spec["snow_provinces_sc1"])
    print("[OK] province_ref selfcheck passed")
    print(f"  snow={len(snow)} warm={49-len(snow)} stream_off={STREAM_OFF}")


if __name__ == "__main__":
    selfcheck()
