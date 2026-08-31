# -*- coding: utf-8 -*-
"""_probe_184b.py — dump remaining relation-delta functions for 续184."""
import os, sys
from _dis_helper import disasm

def dump(va, n, label):
    print("="*70)
    print(f"{label}  @0x{va:06x}  ({n} bytes)")
    print("="*70)
    for r in disasm(va, n):
        print(f"  0x{r['va']:06x}: {r['mnem']} {r['ops']}")

if __name__ == "__main__":
    dump(0x4aa690, 0x191, "0x4aa690  suitability+dispatch (calls 0x4aa820)")
    dump(0x4ab3c0, 0x180, "0x4ab3c0  ACTION HANDLER (tail)")
    dump(0x49b5b0, 0x70, "0x49b5b0  low-nibble writer of 国政治[prov].byte[0xc]")
    dump(0x49b5d0, 0x70, "0x49b5d0  high-nibble writer of 国政治[prov].byte[0xc]")
    dump(0x4ab300, 0xb0, "0x4ab300  high-nibble value = f(new_level, prov)")
