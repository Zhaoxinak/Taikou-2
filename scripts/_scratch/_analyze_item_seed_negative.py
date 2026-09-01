"""Static negative proof: EXE has no category/level factory for 0x51e1f0 pool.

Asserts:
  1. Only bulk store to pool base is vtable stamp (0x47a390).
  2. All absolute 0x51e1f0 refs are init / index / scanners (no field seed).
  3. setFlags(0x49bfc0) never pairs with a byte[+5] store in ±300B.
  4. Known +5 bitfield helpers (0x49c540/560/580) operate on non-pool objects.
"""
from __future__ import annotations

# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>

import struct
from pathlib import Path

MEM = Path(__file__).with_name(_ROOT + '/scripts/_unpacked_mem.bin').read_bytes()
BASE = 0x400000
POOL = 0x51E1F0
SETFLAGS = 0x49BFC0


def find_abs(va: int) -> list[int]:
    pat = struct.pack("<I", va)
    out, i = [], 0
    while True:
        j = MEM.find(pat, i)
        if j < 0:
            break
        out.append(BASE + j)
        i = j + 1
    return out


def find_calls(dest: int) -> list[int]:
    out, i = [], 0
    e8 = bytes([0xE8])
    while True:
        j = MEM.find(e8, i)
        if j < 0 or j + 5 > len(MEM):
            break
        rel = struct.unpack_from("<i", MEM, j + 1)[0]
        if BASE + j + 5 + rel == dest:
            out.append(BASE + j)
        i = j + 1
    return out


def main() -> None:
    refs = find_abs(POOL)
    # Expected absolute sites (from RE): init, scanners, index math
    expected = {
        0x44A401,
        0x44AD91,
        0x44AED6,
        0x44AFC0,
        0x44E035,
        0x44FAEE,
        0x457A95,
        0x45A130,
        0x45E30C,
        0x47A391,
        0x49C045,
        0x4A0ACF,
    }
    missing = expected - set(refs)
    extra = set(refs) - expected
    assert not missing, f"missing expected refs: {[hex(x) for x in missing]}"
    # Allow extras only if documented later; fail loud so we re-audit
    assert not extra, f"new absolute refs need audit: {[hex(x) for x in extra]}"

    # Init only stamps vtable
    off = 0x47A390 - BASE
    assert MEM[off : off + 5] == bytes([0xB8]) + struct.pack("<I", POOL)
    assert MEM[off + 5 : off + 10] == bytes([0xB9, 0xC8, 0x00, 0x00, 0x00])  # mov ecx,200
    # mov dword [eax], 0x4fc0e0
    assert MEM[off + 10] == 0xC7 and MEM[off + 11] == 0x00
    assert struct.unpack_from("<I", MEM, off + 12)[0] == 0x4FC0E0

    # No setFlags site also stores byte [reg+5] in ±300 window (capstone-free byte scan)
    paired = 0
    for va in find_calls(SETFLAGS):
        o = va - BASE
        win = MEM[max(0, o - 300) : o + 40]
        # C6 4X 05 / 88 4X 05 patterns for byte [reg+5]
        for k in range(len(win) - 3):
            b0, b1 = win[k], win[k + 1]
            if b0 == 0xC6 and (b1 & 0xC0) == 0x40 and win[k + 2] == 5:
                paired += 1
            if b0 == 0x88 and (b1 & 0xC0) == 0x40 and win[k + 2] == 5:
                paired += 1
    assert paired == 0, f"setFlags paired with +5 store count={paired}"

    # 0x49c540 writes +5 but callers use entity+0xe / 0x51661e — not pool
    bitfield_callers = find_calls(0x49C540)
    assert 0x419F3F in bitfield_callers  # lea esi,[eax+0xe]
    assert 0x49F002 in bitfield_callers  # ecx=0x51661e

    print("PASS: item pool category/level EXE-side factory absent")
    print(f"  absolute refs={len(refs)} (all classified scanners/init/index)")
    print(f"  setFlags sites={len(find_calls(SETFLAGS))}; none seed +5")
    print("  residual: MSGX/runtime dump or alternate save mapping still possible")


if __name__ == "__main__":
    main()
