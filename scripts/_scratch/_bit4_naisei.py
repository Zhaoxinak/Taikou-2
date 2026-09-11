#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.chdir(r"F:\Games\Taikou 2")
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

code = open("scripts/_unpacked_mem.bin", "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True
texts = json.load(open("scripts/msgx_all_texts.json", encoding="utf-8"))["texts"]
out = open("scripts/_scratch/_bit4_naisei.txt", "w", encoding="utf-8")


def dump(va, n, title=""):
    out.write(f"\n=== {title or hex(va)} ===\n")
    for i in md.disasm(code[va - BASE : va - BASE + n], va):
        out.write(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}\n")
        if i.mnemonic == "push":
            try:
                v = int(i.op_str, 16) if i.op_str.startswith("0x") else int(i.op_str)
                if 0x100 <= v <= 0x3000:
                    out.write(f"    MSG {v:#x} {texts.get(str(v), '')[:100]}\n")
            except ValueError:
                pass


dump(0x4C9F10, 0x80, "4c9f10 decide bit3 vs bit4")
dump(0x4C9F30, 0x80, "4c9f30")
dump(0x4C9280, 0x120, "4c9280 bit4 gate job")
dump(0x4B4580, 0x80, "4b4580 bit3 gate")
# who calls 0x4ca0c0
import struct


def callers(t):
    hits = []
    for i in range(len(code) - 5):
        if code[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", code, i + 1)[0]
        if BASE + i + 5 + rel == t:
            hits.append(BASE + i)
    return hits


out.write("\ncallers 0x4ca0c0: " + ", ".join(hex(h) for h in callers(0x4CA0C0)) + "\n")
out.write("callers 0x4c9f10: " + ", ".join(hex(h) for h in callers(0x4C9F10)) + "\n")
for h in callers(0x4CA0C0)[:8]:
    dump(h - 0x40, 0x50, f"caller {h:#x}")

# 内政 command name table near 工事
for va in range(0x504700, 0x504800, 4):
    raw = code[va - BASE : va - BASE + 8]
    if raw[0] >= 0x80 or (0x20 <= raw[0] < 0x7f):
        try:
            s = raw.split(b"\x00")[0].decode("gbk", "replace")
            if len(s) >= 2:
                out.write(f"str {va:#x}: {s}\n")
        except Exception:
            pass

out.close()
print("ok")
