#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe entity +0x1c..+0x20 accessors and matrix writers."""
import os, struct
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

code = open("scripts/_unpacked_mem.bin", "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def dis(va, n=0x40):
    print(f"--- {hex(va)} ---")
    for i in md.disasm(code[va-BASE:va-BASE+n], va):
        print(f"  {i.address:08x}  {i.mnemonic:8s} {i.op_str}")
        if i.mnemonic.startswith("ret") and i.address > va:
            break

# Known: entity +0x20 = max HP (续241), +0x21 = current HP
# BSDATA stream 0x2c -> entity +0x20 per decoder?
# Check decoder 0x47f7b0 field map / bsdata_format

# Find setters for +0x1c..+0x20 in 0x49a6xx..0x49bxxx library
print("=== setter library around +0x1c..+0x20 ===")
for va in range(0x49a600, 0x49ac00, 0x10):
    s = list(md.disasm(code[va-BASE:va-BASE+0x10], va))
    blob = " ; ".join(f"{i.mnemonic} {i.op_str}" for i in s[:4])
    if any(f"+ 0x{off:x}" in blob or f"+ {off}" in blob for off in (0x1c,0x1d,0x1e,0x1f,0x20,0x21)):
        if "byte ptr [ecx" in blob or "word ptr [ecx" in blob:
            print(hex(va), blob)

# Matrix writers
print("\n=== matrix writers ===")
for va in [0x4a0ff0, 0x4a1010, 0x4a1030, 0x4a0ef0, 0x4a0f10]:
    dis(va, 0x50)

# Count callers of writers
print("\n=== callers ===")
for target in [0x4a0ff0, 0x4a1010, 0x4a1030]:
    sites=[]
    for i in range(len(code)-5):
        if code[i]==0xE8:
            rel=int.from_bytes(code[i+1:i+5],"little",signed=True)
            if BASE+i+5+rel==target:
                sites.append(BASE+i)
    print(hex(target), "n=", len(sites), [hex(s) for s in sites[:12]])
