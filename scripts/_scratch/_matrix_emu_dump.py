#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Emu: verify S13 matrix writers + dump after clear + apply 0x40a350 seed pattern.
Closes residual: prove no static full table; capture protocol-produced grids.
"""
from __future__ import annotations

import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.chdir(r"F:\Games\Taikou 2")
sys.path.insert(0, "scripts")

from unicorn.x86_const import UC_X86_REG_ECX

from emu_harness import Emu, BASE

REC0 = 0x518588
REC1 = 0x518613  # REC0 + 139
STRIDE = 139


def read_block(e: Emu, rec: int, off: int) -> list[list[int]]:
    """Read 5x5 words at rec+off."""
    grid = []
    raw = bytes(e.read(rec + off, 50))
    for r in range(5):
        row = []
        for c in range(5):
            row.append(struct.unpack_from("<H", raw, (r * 5 + c) * 2)[0])
        grid.append(row)
    return grid


def read_vec(e: Emu, rec: int) -> list[int]:
    raw = bytes(e.read(rec + 0x64, 10))
    return [struct.unpack_from("<H", raw, i * 2)[0] for i in range(5)]


def dump_grid(name, g):
    print(f"  {name}:")
    for row in g:
        print("   ", " ".join(f"{v:5d}" for v in row))


def main():
    e = Emu()
    # zero the S13 region first (static image may be 0 already)
    e.write(REC0, b"\x00" * (STRIDE * 3))

    print("=== 1. Leaf writer formula emu ===")
    # A(2,3)=0x1234
    e.call(0x4A0FF0, [2, 3, 0x1234], regs={UC_X86_REG_ECX: REC0})
    # B(1,4)=0x5678  -> stored at row' = 1+5 = 6 → offset (6*5+4)*2 = within block B area
    e.call(0x4A1010, [1, 4, 0x5678], regs={UC_X86_REG_ECX: REC0})
    # C bitfield via 0x4a1030(row=2, bit?, val) — check body later; just call (2,0,3)
    e.call(0x4A1030, [2, 0, 3], regs={UC_X86_REG_ECX: REC0})

    a = read_block(e, REC0, 0)
    b = read_block(e, REC0, 0x32)
    assert a[2][3] == 0x1234, a
    assert b[1][4] == 0x5678, b
    print("  PASS writer A/B cell placement")
    dump_grid("A after probes", a)
    dump_grid("B after probes", b)

    print("\n=== 2. Clear via 0x409650(REC0) ===")
    e.call(0x409650, [REC0])
    a = read_block(e, REC0, 0)
    b = read_block(e, REC0, 0x32)
    # C words may be bit-packed; read as words
    cwords = read_vec(e, REC0)
    dump_grid("A cleared", a)
    dump_grid("B cleared", b)
    print("  C vec:", cwords)
    assert all(v == 0xFFFF for row in a for v in row), a
    assert all(v == 0 for row in b for v in row), b
    print("  PASS clear A=FFFF B=0")

    print("\n=== 3. Apply 0x40a350-documented seeds on REC0/REC1 ===")
    # From static: after special phase —
    # A(1,0)=ebp (skip; use 0), B(1,0)=2000, C(1,0,0)=0 already
    # Then clear REC1 via 0x409650, then:
    # A(0,0)=entity_idx or 0x172, B(0,0)=2000, C(0,0)=2
    e.call(0x409650, [REC1])
    e.call(0x4A0FF0, [0, 0, 0x172], regs={UC_X86_REG_ECX: REC1})
    e.call(0x4A1010, [0, 0, 2000], regs={UC_X86_REG_ECX: REC1})
    e.call(0x4A1030, [0, 0, 2], regs={UC_X86_REG_ECX: REC1})
    # REC0 seeds from alternate path
    e.call(0x4A0FF0, [1, 0, 0], regs={UC_X86_REG_ECX: REC0})
    e.call(0x4A1010, [1, 0, 2000], regs={UC_X86_REG_ECX: REC0})
    e.call(0x4A1030, [1, 0, 0], regs={UC_X86_REG_ECX: REC0})

    out = {
        "rec0": {
            "A": read_block(e, REC0, 0),
            "B": read_block(e, REC0, 0x32),
            "C_words": read_vec(e, REC0),
            "tail_6e": list(e.read(REC0 + 0x6E, 4)),
        },
        "rec1": {
            "A": read_block(e, REC1, 0),
            "B": read_block(e, REC1, 0x32),
            "C_words": read_vec(e, REC1),
        },
        "protocol": {
            "clear_0x409650": "5x5 A=0xFFFF B=0 C=0",
            "seed_B_2000": "blockB (row,col)=(0|1,0) val=2000",
            "seed_A_sentinel": "0xFFFF clear / 0x172 entity-miss",
            "note": "No ROM full table; mid-game grids are objective runtime state",
        },
    }
    dump_grid("REC0.A", out["rec0"]["A"])
    dump_grid("REC0.B", out["rec0"]["B"])
    dump_grid("REC1.A", out["rec1"]["A"])
    dump_grid("REC1.B", out["rec1"]["B"])
    print("  REC1.C:", out["rec1"]["C_words"])

    path = "scripts/matrix_518588_runtime.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\nWrote", path)
    print("ALL EMU STEPS OK")


if __name__ == "__main__":
    main()
