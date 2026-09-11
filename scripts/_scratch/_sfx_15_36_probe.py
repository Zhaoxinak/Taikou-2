#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe: enumerate indirect play_sfx call sites and trace args for 15/36."""
import os, struct, re, pickle
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # scripts/
ROOT = os.path.dirname(HERE)
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
PLAY = 0x4997c0
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

INSNS, FUNCS = pickle.load(open(os.path.join(HERE, "_insn_addrs.pkl"), "rb"))


def rva(va):
    return va - BASE


def va_of(r):
    return BASE + r


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


def prev_insns(call_va, nbytes=0x80, maxn=40):
    cr = rva(call_va)
    prev = []
    r = cr
    for _ in range(maxn):
        found = None
        for back in range(1, 16):
            if (r - back) in INSNS:
                found = r - back
                break
        if found is None:
            break
        size, txt = INSNS[found]
        prev.append((va_of(found), size, txt))
        r = found
        if va_of(found) < call_va - nbytes:
            break
    prev.reverse()
    return prev


sites = find_calls(PLAY)
print("total sites", len(sites))

indirect = []
direct = {}
noalign = []

for call_va in sites:
    cr = rva(call_va)
    if cr not in INSNS:
        noalign.append(call_va)
        continue
    prev = prev_insns(call_va)
    last_push = None
    for va, size, txt in prev:
        if txt.startswith("push "):
            last_push = (va, txt)
    if last_push is None:
        indirect.append((call_va, None, "NO_PUSH", prev[-12:]))
        continue
    op = last_push[1][5:].strip()
    imm = imm_val(op)
    if imm is not None:
        direct.setdefault(imm, []).append(call_va)
    else:
        indirect.append((call_va, last_push[0], op, prev[-16:]))

print(
    "direct imm unique IDs",
    sorted(k for k in direct if 0 <= k < 39),
    "count sites",
    sum(len(v) for v in direct.values()),
)
print("indirect count", len(indirect))
print("noalign", [hex(x) for x in noalign])
print()
print("=== INDIRECT DETAIL ===")
for call_va, push_va, op, prev in indirect:
    print(f"\n--- call {hex(call_va)} push {hex(push_va) if push_va else None} arg={op} ---")
    for va, size, txt in prev:
        mark = " *" if push_va and va == push_va else "   "
        print(f"{mark} {hex(va)}: {txt}")
    print(f">>> {hex(call_va)}: call 0x4997c0")

# Also dump wider context for each indirect site (function-ish)
print("\n\n=== WIDER CONTEXT (0x100 before each indirect) ===")
for call_va, push_va, op, _ in indirect:
    print(f"\n##### {hex(call_va)} arg={op} #####")
    for va, size, txt in prev_insns(call_va, nbytes=0x120, maxn=80):
        mark = " *" if push_va and va == push_va else (">>>" if va == call_va else "   ")
        print(f"{mark} {hex(va)}: {txt}")
    print(f">>> {hex(call_va)}: call 0x4997c0")
    # a few after
    r = rva(call_va)
    size, txt = INSNS[r]
    r2 = r + size
    for _ in range(8):
        if r2 not in INSNS:
            break
        s, t = INSNS[r2]
        print(f"    {hex(va_of(r2))}: {t}")
        r2 += s
