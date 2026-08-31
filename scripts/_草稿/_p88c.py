# -*- coding: utf-8 -*-
"""0x4ab680 success-branch detail: how 0x49fe40 is reached + newlevel computation."""
import os
from _dis_helper import disasm

print("=== 0x4ab680 success branch (0x4ab700 .. 0x4ab960) ===")
for r in disasm(0x4ab680, 0x300):
    if r["va"] >= 0x4ab700:
        tag = "  <-- CALL 0x%s" % r["tgt"] if r["mnem"] == "call" else ""
        print("0x%x  %-8s %s%s" % (r["va"], r["mnem"], r["ops"], tag))
