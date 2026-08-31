# -*- coding: utf-8 -*-
"""Dump 0x4ab680 call targets + full disasm (relation action gate)."""
import os
from _dis_helper import disasm

print("=== 0x4ab680 calls ===")
seen=set()
for r in disasm(0x4ab680, 0x300):
    if r["mnem"]=="call":
        t=r["tgt"]
        if t not in seen:
            seen.add(t); print("  0x%x : call 0x%s" % (r["va"], t))

print()
print("=== 0x4ab680 full (first 80 insn) ===")
n=0
for r in disasm(0x4ab680, 0x300):
    print("0x%x  %-8s %s" % (r["va"], r["mnem"], r["ops"]))
    n+=1
    if n>=80: break
