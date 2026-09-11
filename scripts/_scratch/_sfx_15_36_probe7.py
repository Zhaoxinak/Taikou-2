#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe7: indirect call/jmp to play_sfx; cross-check 26/32/37; finalize facts."""
import os, struct, re, pickle
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_IMM, CS_OP_REG

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
PLAY = 0x4997c0
INNER = 0x499740
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True
INSNS, FUNCS = pickle.load(open(os.path.join(HERE, "_insn_addrs.pkl"), "rb"))


def rd(va, n):
    o = va - BASE
    return MEM[o : o + n] if 0 <= o and o + n <= len(MEM) else b""


# Scan ALL call/jmp instructions in INSNS for target PLAY
print("=== INSNS scan for transfers to play_sfx / play_inner ===")
hits = []
for rva, (size, txt) in INSNS.items():
    if not (txt.startswith("call ") or txt.startswith("jmp ")):
        continue
    op = txt.split(" ", 1)[1].strip()
    # direct imm
    if op.startswith("0x"):
        try:
            t = int(op, 16)
        except ValueError:
            continue
        if t in (PLAY, INNER):
            hits.append((BASE + rva, txt, t))
print("direct call/jmp count:", len(hits))
print("  to play:", sum(1 for h in hits if h[2] == PLAY))
print("  to inner:", sum(1 for h in hits if h[2] == INNER))

# Indirect: call eax / call [mem] — see if any load PLAY address nearby
print("\n=== mov reg, play_sfx imm32 then call reg ===")
# B8 xx xx xx xx = mov eax, imm32 etc.
play_le = struct.pack("<I", PLAY)
inner_le = struct.pack("<I", INNER)
for label, needle in [("play", play_le), ("inner", inner_le)]:
    off = 0
    locs = []
    while True:
        i = MEM.find(needle, off)
        if i < 0:
            break
        locs.append(BASE + i)
        off = i + 1
    print(f"  dword {label} occurrences: {len(locs)}")
    # classify context: in code as imm operand?
    codeish = []
    for va in locs:
        # check byte before for mov-imm opcode
        prev = rd(va - 1, 1)
        if prev in (b"\xb8", b"\xb9", b"\xba", b"\xbb", b"\xbe", b"\xbf"):  # mov r32, imm32
            codeish.append((hex(va - 1), f"mov r32, {label}"))
        elif rd(va - 1, 1) == b"\x68":  # push imm32
            codeish.append((hex(va - 1), f"push {label}"))
        elif rd(va - 2, 2) in (b"\xc7\x00", b"\xc7\x05", b"\xc7\x01", b"\xc7\x02", b"\xc7\x03", b"\xc7\x06", b"\xc7\x07"):
            codeish.append((hex(va - 2), f"mov mem, {label}"))
    print(f"  code-like embeds: {codeish[:20]} n={len(codeish)}")

# Confirm SFX name table is ONLY consumer of the two strings
SFX_TBL = 0x50ba40
print("\n=== name table slots 15 and 36 ===")
for i in (15, 36):
    p = struct.unpack_from("<I", MEM, SFX_TBL - BASE + 4 * i)[0]
    s = rd(p, 16).split(b"\x00")[0].decode("ascii", "replace")
    print(f"  [{i}] ptr={hex(p)} str={s}")

# Document resolved coverage after REG sites
print("\n=== coverage after resolving 5 REG sites ===")
resolved = {
    0: "IMM + REG@0x422a17 (ebx=0)",
    19: "REG@0x46bd3c/c3/e37 ebp=0x13",
    20: "REG@0x46bd3c/c3/e37 ebp=0x14",
    34: "REG@0x44edd4 ecx=0x22",
    35: "REG@0x44edd4 ecx=0x23",
}
still = [15, 26, 32, 36, 37]
print("newly resolved via REG:", resolved)
print("still no static producer:", still)

# Double-check: are there ANY push 15/36 where the FOLLOWING call is play_sfx
# (not just within 0x30)
print("\n=== push 15/36 followed by call play_sfx within 0x10 bytes (strict) ===")
for imm in (15, 36):
    needle = bytes([0x6A, imm])
    off = 0
    while True:
        i = MEM.find(needle, off)
        if i < 0:
            break
        pva = BASE + i
        # disasm and find next call
        for j in range(2, 0x10):
            if rd(pva + j, 1) == b"\xe8":
                rel = struct.unpack_from("<i", MEM, pva + j - BASE + 1)[0]
                tgt = (pva + j + 5 + rel) & 0xFFFFFFFF
                if tgt == PLAY:
                    print(f"  HIT push {imm} @{hex(pva)} -> play")
                break
        off = i + 1
print("(no lines above => zero hits)")

# Also check push imm32 form: 68 0F 00 00 00 / 68 24 00 00 00
for imm in (15, 36):
    needle = struct.pack("<BI", 0x68, imm)
    off = 0
    hits2 = []
    while True:
        i = MEM.find(needle, off)
        if i < 0:
            break
        pva = BASE + i
        for j in range(5, 0x14):
            if rd(pva + j, 1) == b"\xe8":
                rel = struct.unpack_from("<i", MEM, pva + j - BASE + 1)[0]
                tgt = (pva + j + 5 + rel) & 0xFFFFFFFF
                if tgt == PLAY:
                    hits2.append(hex(pva))
                break
        off = i + 1
    print(f"push imm32 {imm} near play: {hits2}")
