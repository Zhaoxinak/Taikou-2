#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe4: callers of 0x46bc00; scan for 15/36 as args; recount unnamed's 10."""
import os, struct, re, pickle
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
PLAY = 0x4997c0
TARGET = 0x46bc00  # thiscall; ret 0xc; arg1 can be SFX id
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


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


def imm_val(tok):
    tok = tok.strip()
    m = re.fullmatch(r"(0x[0-9a-fA-F]+|[0-9]+)", tok)
    if not m:
        return None
    s = m.group()
    return int(s, 16) if s.lower().startswith("0x") else int(s)


def decode_before(call_va, before=0x40):
    start = call_va - before
    raw = rd(start, before + 8)
    best = None
    for off in range(before + 1):
        ins = list(md.disasm(raw[off:], start + off))
        addrs = [i.address for i in ins]
        if call_va not in addrs:
            continue
        idx = addrs.index(call_va)
        if best is None or idx > best[0]:
            best = (idx, ins)
    return best[1][: best[0] + 1] if best else []


# --- callers of 0x46bc00 ---
callers = find_calls(TARGET)
print(f"callers of {hex(TARGET)}: {len(callers)}")
for c in callers:
    ins = decode_before(c, before=0x50)
    print(f"\n=== call {hex(c)} ===")
    for i in ins[-18:]:
        mark = ">>>" if i.address == c else "   "
        print(f"{mark} {hex(i.address)}: {i.mnemonic} {i.op_str}")
    # extract last 3 pushes (stdcall/thiscall stack args; this in ecx)
    pushes = [i for i in ins if i.mnemonic == "push"]
    last3 = pushes[-3:] if len(pushes) >= 3 else pushes
    print("  last pushes:", [(hex(p.address), p.op_str) for p in last3])
    # check if any push is 15 or 36
    for p in pushes:
        v = imm_val(p.op_str)
        if v in (15, 36, 0x0F, 0x24, 19, 20, 0x13, 0x14):
            print(f"  !! interesting push {v} at {hex(p.address)}")

# Also find call [mem] / indirect to 0x46bc00 via pointer tables?
print("\n=== ptr xrefs to 0x46bc00 in data ===")
needle = struct.pack("<I", TARGET)
offs = []
off = 0
while True:
    i = MEM.find(needle, off)
    if i < 0:
        break
    offs.append(BASE + i)
    off = i + 1
print([hex(x) for x in offs[:40]], "count", len(offs))

# Recreate unnamed's "10 indirect" count
print("\n=== recount sites with no push-imm (unnamed口径) ===")
sites = find_calls(PLAY)


def arg_immediate(call_va, span=0x40):
    best = None
    for back in range(1, span):
        start = call_va - back
        try:
            ins = list(md.disasm(rd(start, back + 16), start))
        except Exception:
            continue
        idx = None
        for k, i in enumerate(ins):
            if i.address == call_va:
                idx = k
                break
        if idx is None:
            continue
        pushes = []
        for i in ins[:idx]:
            if i.mnemonic == "push":
                v = imm_val(i.op_str)
                if v is not None:
                    pushes.append((i.address, v))
        if pushes:
            best = (back, pushes[-1][1])
    return best[1] if best else None


no_imm = []
for va in sites:
    a = arg_immediate(va)
    if a is None:
        no_imm.append(va)
print("no-imm count:", len(no_imm))
for va in no_imm:
    ins = decode_before(va, 0x30)
    pushes = [(hex(i.address), i.op_str) for i in ins if i.mnemonic == "push"]
    print(f"  {hex(va)} pushes={pushes[-3:]}")

# Search ALL push 0x0f / push 0x24 and see what function is called after
print("\n=== all push 15 then call <fn> (first call after) ===")


def next_call_after(push_va, limit=0x20):
    ins = list(md.disasm(rd(push_va, limit), push_va))
    for i in ins:
        if i.mnemonic == "call":
            return i.address, i.op_str
    return None, None


for imm in (0x0F, 0x24):
    needle = bytes([0x6A, imm])
    off = 0
    pairs = {}
    while True:
        i = MEM.find(needle, off)
        if i < 0:
            break
        pva = BASE + i
        # verify it's really push imm via disasm at that addr
        ins0 = list(md.disasm(rd(pva, 8), pva))
        if not ins0 or ins0[0].mnemonic != "push" or imm_val(ins0[0].op_str) != imm:
            off = i + 1
            continue
        ca, op = next_call_after(pva)
        key = op or "?"
        pairs.setdefault(key, []).append(hex(pva))
        off = i + 1
    print(f"\npush {imm}:")
    for k, v in sorted(pairs.items(), key=lambda x: -len(x[1])):
        print(f"  call {k}: n={len(v)} e.g. {v[:5]}")
