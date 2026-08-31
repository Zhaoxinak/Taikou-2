# -*- coding: utf-8 -*-
"""Dump relation-write chain under 0x4ab680: 0x49fe40(set_diplomacy), 0x4ab9e0, gates."""
import os
from _dis_helper import disasm

def dump(va, size, name):
    print("=== %s @0x%x (0x%x) ===" % (name, va, size))
    for r in disasm(va, size):
        tag = ""
        if r["mnem"] == "call":
            tag = "  <-- CALL 0x%s" % r["tgt"]
        print("0x%x  %-8s %s%s" % (r["va"], r["mnem"], r["ops"], tag))
    print()

dump(0x49fe40, 0x60, "0x49fe40 set_diplomacy")
dump(0x4ab9e0, 0x90, "0x4ab9e0")
dump(0x4ab7a0, 0x50, "0x4ab7a0 gate1")
dump(0x4ab830, 0x40, "0x4ab830 gate2")
dump(0x4ab850, 0x40, "0x4ab850 gate3")
