#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe3: deep-dive ebp sites, push-0xf near call, tables with 15/36, wrappers."""
import os, struct, re, pickle
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
PLAY = 0x4997c0
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True
INSNS, FUNCS = pickle.load(open(os.path.join(HERE, "_insn_addrs.pkl"), "rb"))
FUNCS_S = sorted(FUNCS)


def rd(va, n):
    o = va - BASE
    return MEM[o : o + n] if 0 <= o and o + n <= len(MEM) else b""


def find_calls(target):
    out = []
    off = 0
    while True:
        i = MEM.find(b"\xE8", off)
        if i < 0:
            break
        rel = struct.unpack_from("<i", MEM, i + 1)[0]
        if (BASE + i + 5 + rel) & 0xFFFFFFFF == target:
            out.append(BASE + i)
        off = i + 1
    return out


def containing_func(va):
    # FUNCS appear to be VAs or RVAs?
    # check a sample
    cand = [f for f in FUNCS_S if f <= va]
    if not cand:
        # try RVA
        r = va - BASE
        cand = [f for f in FUNCS_S if f <= r]
        if cand:
            return BASE + cand[-1], True
        return None, False
    # if funcs look like VAs (>= BASE)
    if FUNCS_S[-1] > BASE:
        return cand[-1], False
    return BASE + cand[-1], True


def disasm_range(start, end):
    raw = rd(start, end - start)
    return list(md.disasm(raw, start))


def dump_func_around(va, back=0x200, fwd=0x80):
    # prefer INSNS walk if available
    r = va - BASE
    if r in INSNS:
        # walk back
        out = []
        cur = r
        collected = []
        for _ in range(200):
            found = None
            for b in range(1, 16):
                if (cur - b) in INSNS:
                    found = cur - b
                    break
            if found is None:
                break
            collected.append(found)
            cur = found
            if BASE + found < va - back:
                break
        collected.reverse()
        for fr in collected:
            s, t = INSNS[fr]
            out.append((BASE + fr, t))
        # forward
        cur = r
        for _ in range(40):
            if cur not in INSNS:
                break
            s, t = INSNS[cur]
            out.append((BASE + cur, t))
            cur += s
            if BASE + cur > va + fwd:
                break
        return out
    # fallback window
    start = va - back
    ins = list(md.disasm(rd(start, back + fwd), start))
    return [(i.address, f"{i.mnemonic} {i.op_str}") for i in ins]


print("FUNCS sample:", FUNCS_S[:5], "...", FUNCS_S[-3:], "n=", len(FUNCS_S))
print("FUNCS look like RVA?" , FUNCS_S[0] < BASE)

# 1) Look at push 0xf near 0x421fba
print("\n=== context around push 0x0f @0x421f8e / call @0x421fba ===")
for addr, txt in dump_func_around(0x421fba, back=0x80, fwd=0x30):
    mark = ">>>" if addr == 0x421fba else (" !" if addr == 0x421f8e else "   ")
    print(f"{mark} {hex(addr)}: {txt}")

# 2) Trace ebp for function containing 0x46bd3c
print("\n=== ebp provenance in func around 0x46bd3c ===")
# find function start via prologue search
# Look for push ebp / mov ebp, esp before, or use FUNCS
fva, is_rva = containing_func(0x46bd3c)
print("containing_func guess:", hex(fva) if fva else None, "is_rva_key", is_rva)

# Dump from likely function start: search back for common prologue
start_guess = None
for back in range(0, 0x800, 1):
    a = 0x46bd3c - back
    b = rd(a, 3)
    # push ebp; mov ebp, esp = 55 8B EC
    if b == b"\x55\x8b\xec":
        start_guess = a
        break
    # sub esp, imm with prior pushes
print("prologue 55 8B EC found at:", hex(start_guess) if start_guess else None)

# Broader: find where ebp is assigned before the three push ebp calls
print("\n--- scanning 0x46ba00..0x46bf00 for ebp writes / movs ---")
ins = list(md.disasm(rd(0x46ba00, 0x500), 0x46ba00))
for i in ins:
    if "ebp" in i.op_str and i.mnemonic in (
        "mov", "lea", "xor", "add", "sub", "and", "or", "imul", "movzx", "movsx", "pop"
    ):
        # only writes to ebp (dest)
        dest = i.op_str.split(",")[0].strip()
        if dest == "ebp" or dest.startswith("ebp"):
            print(f"  {hex(i.address)}: {i.mnemonic} {i.op_str}")
    if i.mnemonic == "call" and i.op_str.strip() in ("0x4997c0",):
        print(f"  CALL {hex(i.address)}: {i.mnemonic} {i.op_str}")

# Full dump of function from start_guess or 0x46bc00
dump_start = start_guess or 0x46bc00
print(f"\n=== full dump from {hex(dump_start)} ===")
for i in md.disasm(rd(dump_start, 0x46bf00 - dump_start), dump_start):
    if i.address > 0x46be80:
        break
    mark = ""
    if i.address in (0x46bd3c, 0x46bdc3, 0x46be37, 0x46be19):
        mark = " >>>PLAY"
    if i.mnemonic == "push" and "ebp" in i.op_str:
        mark = " *PUSH_EBP"
    print(f"{hex(i.address)}: {i.mnemonic} {i.op_str}{mark}")

# 3) ebx at 0x422a17 — find ebx zeroing
print("\n=== ebx provenance near 0x422a17 ===")
for addr, txt in dump_func_around(0x422a17, back=0x200, fwd=0x20):
    if "ebx" in txt or addr == 0x422a17 or "xor" in txt:
        mark = ">>>" if addr == 0x422a17 else "   "
        print(f"{mark} {hex(addr)}: {txt}")

# 4) Search for byte/word tables that contain both or either 15 and 36
# Look for sequences of small ints that look like SFX id lists
print("\n=== search data for lone 0x0F / 0x24 as potential SFX id stores ===")
# Look for: mov [mem], 0x0f / mov word/byte patterns C7 / C6
# Also: tables of bytes including 0x0f and 0x24 consecutively-ish

# Find xrefs: any instruction that has immediate 15 or 36 being stored then later used?
# Search for `push 0x0f` that is NOT near play_sfx - those might set a field

sites = find_calls(PLAY)
print("play_sfx sites", len(sites))

# Wrappers: functions that take an arg and call play_sfx with it
print("\n=== candidate wrappers (push reg/mem then call play_sfx) ===")
for va, info_note in [
    (0x422a17, "ebx"),
    (0x44edd4, "ecx=0x22/23"),
    (0x46bd3c, "ebp"),
    (0x46bdc3, "ebp"),
    (0x46be37, "ebp"),
]:
    print(f"  {hex(va)}: {info_note}")

# Is play_sfx also reached via jmp?
print("\n=== jmp/call* to play_sfx ===")
# E9 rel32
off = 0
jmps = []
while True:
    i = MEM.find(b"\xE9", off)
    if i < 0:
        break
    rel = struct.unpack_from("<i", MEM, i + 1)[0]
    if (BASE + i + 5 + rel) & 0xFFFFFFFF == PLAY:
        jmps.append(BASE + i)
    off = i + 1
print("direct jmp sites:", [hex(x) for x in jmps])

# FF 15 abs call / FF 25 abs jmp — unlikely for internal

# 5) Look who writes SFX id into a struct field that ebp reads
# First need ebp value origin in the 0x46bd function
