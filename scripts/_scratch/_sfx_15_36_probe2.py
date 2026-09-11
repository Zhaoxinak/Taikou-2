#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe2: analyze noalign + all non-imm play_sfx sites thoroughly."""
import os, struct, re, pickle
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
PLAY = 0x4997c0
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True
INSNS, FUNCS = pickle.load(open(os.path.join(HERE, "_insn_addrs.pkl"), "rb"))


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


def decode_window(call_va, before=0x60, after=0x20):
    """Disassemble a window ending at call; return list of insns that include the call."""
    start = call_va - before
    raw = rd(start, before + after)
    # Try every start offset for alignment that lands on call
    best = None
    for off in range(before + 1):
        ins = list(md.disasm(raw[off:], start + off))
        addrs = [i.address for i in ins]
        if call_va not in addrs:
            continue
        idx = addrs.index(call_va)
        # score: prefer more valid-looking pushes before call
        score = idx
        if best is None or score > best[0]:
            best = (score, ins, idx)
    if best is None:
        return None, None
    return best[1], best[2]


def classify_arg(call_va):
    ins, idx = decode_window(call_va)
    if ins is None:
        return "FAIL", None, []
    pushes = []
    for i in ins[:idx]:
        if i.mnemonic == "push":
            pushes.append(i)
    if not pushes:
        return "NO_PUSH", None, ins[max(0, idx - 12) : idx + 1]
    last = pushes[-1]
    imm = imm_val(last.op_str)
    kind = "IMM" if imm is not None else "IND"
    return kind, (last.address, last.op_str, imm), ins[max(0, idx - 16) : idx + 3]


sites = find_calls(PLAY)
print("total", len(sites))

imm_ids = {}
indirect = []
fail = []

for va in sites:
    kind, info, ctx = classify_arg(va)
    if kind == "IMM":
        imm_ids.setdefault(info[2], []).append(va)
    elif kind == "IND":
        indirect.append((va, info, ctx))
    else:
        fail.append((va, kind, ctx))

print("imm covered (0..38):", sorted(k for k in imm_ids if 0 <= k < 39))
print("imm site count:", sum(len(v) for v in imm_ids.values()))
print("indirect:", len(indirect))
print("fail:", len(fail))
print()

for va, info, ctx in indirect:
    print("=" * 70)
    print(f"IND call@{hex(va)}  push@{hex(info[0])}  arg={info[1]}")
    for i in ctx:
        mark = ">>>" if i.address == va else (" *" if i.address == info[0] else "   ")
        print(f"{mark} {hex(i.address)}: {i.mnemonic} {i.op_str}")

print("\n\nFAILS:")
for va, kind, ctx in fail:
    print(f"  {hex(va)} {kind}")

# Cross-check: which of 15,36 appear as imm?
print("\n15 sites:", [hex(x) for x in imm_ids.get(15, [])])
print("36 sites:", [hex(x) for x in imm_ids.get(36, [])])

# Search whole image for: push 0x0f / push 0x24 (bytes 6A 0F / 6A 24)
# and mov r32, 0x0f / 0x24 near any play_sfx
print("\n=== global imm byte scan ===")
for imm, name in [(0x0F, "15"), (0x24, "36")]:
    needle = bytes([0x6A, imm])
    hits = []
    off = 0
    while True:
        i = MEM.find(needle, off)
        if i < 0:
            break
        hits.append(BASE + i)
        off = i + 1
    print(f"push {imm} (6A {imm:02X}) count={len(hits)}")
    # which are within 0x30 of a play_sfx call?
    near = []
    for h in hits:
        for c in sites:
            if 0 < c - h <= 0x30:
                near.append((hex(h), hex(c)))
    print(f"  within 0x30 before play_sfx: {near}")

# mov reg, imm8/imm32 encodings near calls
# B? xx = mov r32, imm32; C7 ... ; etc — use disasm of 0x40 before each site
print("\n=== mov-imm 15/36 in 0x80 window before each call ===")
for want in (15, 36):
    hits = []
    for c in sites:
        ins, idx = decode_window(c, before=0x80)
        if ins is None:
            continue
        for i in ins[:idx]:
            if i.mnemonic != "mov":
                continue
            # look for , 0xf / , 0x0f / , 0x24 as src
            parts = i.op_str.split(",")
            if len(parts) != 2:
                continue
            v = imm_val(parts[1].strip())
            if v == want:
                hits.append((hex(c), hex(i.address), i.op_str))
    print(f"mov *, {want}: {hits}")
