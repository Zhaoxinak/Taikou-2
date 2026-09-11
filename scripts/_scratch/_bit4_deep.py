#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, struct, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.chdir(r"F:\Games\Taikou 2")
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

code = open("scripts/_unpacked_mem.bin", "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True
texts = json.load(open("scripts/msgx_all_texts.json", encoding="utf-8"))["texts"]
out = open("scripts/_scratch/_bit4_deep.txt", "w", encoding="utf-8")


def dis(va, n=0x100):
    return list(md.disasm(code[va - BASE : va - BASE + n], va))


out.write("=== 0x4ca0a0 (bit3/bit4 wrapper) ===\n")
for i in dis(0x4CA090, 0x80):
    out.write(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")

out.write("\n=== 0x4c9200 bit4 test context ===\n")
for i in dis(0x4C9180, 0x200):
    if 0x4C9180 <= i.address <= 0x4C9380:
        out.write(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")
        if i.mnemonic == "push":
            try:
                v = int(i.op_str, 16) if i.op_str.startswith("0x") else int(i.op_str)
                if 100 <= v <= 8000:
                    out.write(f"    MSG {v:#x} {texts.get(str(v),'')[:90]}\n")
            except ValueError:
                pass

# direct or [reg+0x1c], 0x10 besides setter
out.write("\n=== or [reg+0x1c],0x10 ===\n")
for pat in (b"\x80\x49\x1c\x10", b"\x80\x4e\x1c\x10", b"\x80\x4f\x1c\x10",
            b"\x80\x4b\x1c\x10", b"\x80\x4d\x1c\x10"):
    st = 0
    while True:
        j = code.find(pat, st)
        if j < 0:
            break
        out.write(f"  {BASE+j:08x} {pat.hex()}\n")
        st = j + 1

# or [reg+0x1c], 8
out.write("\n=== or [reg+0x1c],8 ===\n")
for pat in (b"\x80\x49\x1c\x08", b"\x80\x4e\x1c\x08", b"\x80\x4f\x1c\x08",
            b"\x80\x4b\x1c\x08"):
    st = 0
    while True:
        j = code.find(pat, st)
        if j < 0:
            break
        out.write(f"  {BASE+j:08x}\n")
        st = j + 1

# 0x4b45c3 bit3 test - what function (筑城 gate?)
out.write("\n=== 0x4b4500 bit3 gate ===\n")
for i in dis(0x4B4500, 0x100):
    out.write(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")
    if i.mnemonic == "push":
        try:
            v = int(i.op_str, 16) if i.op_str.startswith("0x") else int(i.op_str)
            if 100 <= v <= 8000:
                out.write(f"    MSG {v:#x} {texts.get(str(v),'')[:90]}\n")
        except ValueError:
            pass

# Find who calls 0x49abc0 with push 1 - scan more carefully
out.write("\n=== 0x4ca0e1 detail ===\n")
for i in dis(0x4CA0B0, 0x50):
    out.write(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")

# 0x4d8703 bit3 with ebx - construction related?
out.write("\n=== 0x4d8680 ===\n")
for i in dis(0x4D8680, 0xC0):
    out.write(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")

out.close()
print("ok")
