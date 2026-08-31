# -*- coding: utf-8 -*-
"""_probe_184.py — dump disasm of relation-delta leaf functions for 续184."""
import os, sys
from _dis_helper import disasm

HERE = os.path.dirname(os.path.abspath(__file__))

def dump(va, n, label):
    print("="*70)
    print(f"{label}  @0x{va:06x}  ({n} bytes)")
    print("="*70)
    for r in disasm(va, n):
        print(f"  0x{r['va']:06x}: {r['mnem']} {r['ops']}")

if __name__ == "__main__":
    dump(0x4aa820, 0x140, "0x4aa820  relation-delta leaf (0x4aa690 -> here)")
    dump(0x4ab3c0, 0x180, "0x4ab3c0  action handler (writes 国政治[国].byte[0xc])")
    dump(0x49b5b0, 0x60, "0x49b5b0  low-nibble writer")
    dump(0x49b5d0, 0x60, "0x49b5d0  high-nibble writer")
