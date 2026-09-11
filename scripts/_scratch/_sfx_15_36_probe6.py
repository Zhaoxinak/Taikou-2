#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe6: exhaust all arg forms; prove 15/36 unreachable statically."""
import os, struct, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_IMM, CS_OP_REG, CS_OP_MEM

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
PLAY = 0x4997c0
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


def decode_window(call_va, before=0x60):
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
    return (best[1], best[0]) if best else (None, None)


sites = find_calls(PLAY)
print("sites", len(sites))

rows = []
for c in sites:
    ins, idx = decode_window(c)
    if ins is None:
        rows.append((c, "ALIGN_FAIL", None, None))
        continue
    pushes = [i for i in ins[:idx] if i.mnemonic == "push"]
    if not pushes:
        rows.append((c, "NO_PUSH", None, None))
        continue
    last = pushes[-1]
    ot = last.operands[0].type if last.operands else None
    if ot == CS_OP_IMM:
        rows.append((c, "IMM", last.operands[0].imm, last.op_str))
    elif ot == CS_OP_REG:
        rows.append((c, "REG", last.op_str, last.op_str))
    elif ot == CS_OP_MEM:
        rows.append((c, "MEM", last.op_str, last.op_str))
    else:
        rows.append((c, "OTHER", last.op_str, last.op_str))

from collections import Counter
print("kinds:", Counter(r[1] for r in rows))
print("\nNon-IMM:")
for r in rows:
    if r[1] != "IMM":
        print(f"  {hex(r[0])}: {r[1]} arg={r[2]}")

# Immediate ID coverage
imm_ids = sorted({r[2] for r in rows if r[1] == "IMM" and isinstance(r[2], int) and 0 <= r[2] < 39})
print("\nimm IDs covered:", imm_ids)
print("missing:", sorted(set(range(39)) - set(imm_ids)))

# Proven resolved values for REG sites
print("\n=== proven REG site values ===")
# 0x422a17 ebx=0 (xor ebx,ebx @0x4228c9, no write to ebx before push)
# 0x44edd4 ecx = 0x22 + (edx!=0) => 34/35
# 0x46bd3c/c3/e37 ebp = 0x13 or 0x14 ONLY when those pushes execute
#   (push ebp only on arg1==0 path; on that path ebp set to 0x13/0x14)

# Verify no ebx write between xor and push at 0x422a17
print("--- ebx writes 0x4228c9..0x422a12 ---")
ins, idx = decode_window(0x422a17, before=0x1c0)
for i in ins[:idx]:
    if i.address < 0x4228c9:
        continue
    # dest ebx?
    if i.op_str.startswith("ebx") or (
        i.mnemonic in ("xor", "mov", "lea", "add", "sub", "and", "or", "pop")
        and i.op_str.split(",")[0].strip() == "ebx"
    ):
        print(f"  {hex(i.address)}: {i.mnemonic} {i.op_str}")

# Verify ebp assignment exclusivity: on paths reaching push ebp, is ebp only 0x13/0x14?
# Check: between 0x46bc00 and each push ebp, what writes ebp?
print("\n--- ebp writes in 0x46bc00..0x46be40 ---")
for i in md.disasm(rd(0x46bc00, 0x250), 0x46bc00):
    dest = i.op_str.split(",")[0].strip()
    if dest == "ebp" and i.mnemonic != "push":
        print(f"  {hex(i.address)}: {i.mnemonic} {i.op_str}")

# Control-flow: can we reach push-ebp after mov ebp,[esp+0x18]?
# The mov ebp,[esp+0x18] is at 0x46bc90 on arg1!=0 path.
# push ebp sites: 0x46bd3b, 0x46bdc2, 0x46be36 — each preceded by je from cmp [esp+0x18],0
# So reaching push-ebp requires [esp+0x18]==0, but mov ebp,[esp+0x18] only when arg1!=0
# at entry. After path merge at 0x46bc94, both paths continue. Then at play sites,
# they RE-CHECK [esp+0x18]==0 before push ebp.
# Therefore: push ebp ⇒ [esp+0x18]==0 ⇒ we came from arg1==0 path ⇒ ebp is 0x13 or 0x14.
# The mov ebp,[esp+0x18] value is dead for play_sfx purposes.

print("\n=== search wrappers that call play_sfx with their own arg ===")
# Find functions containing exactly one call to play_sfx with push reg from [esp+N]
# Already have only 5 REG sites.

# Any call to play via bottom layer with ZANSYU/MATISIRO string directly?
Z = MEM.find(b"A:ZANSYU.KOS")
M = MEM.find(b"A:MATISIRO.KOS")
print("ZANSYU str @", hex(BASE + Z) if Z >= 0 else None)
print("MATISIRO str @", hex(BASE + M) if M >= 0 else None)

# xrefs: push imm32 of string address then call something
for name, pos in [("ZANSYU", Z), ("MATISIRO", M)]:
    if pos < 0:
        continue
    va = BASE + pos
    # also check pointer in SFX table
    # find dword references
    needle = struct.pack("<I", va)
    refs = []
    off = 0
    while True:
        i = MEM.find(needle, off)
        if i < 0:
            break
        refs.append(BASE + i)
        off = i + 1
    print(f"  {name} dword xrefs ({len(refs)}):", [hex(x) for x in refs[:15]])

# SFX table slot
SFX_TBL = 0x50ba40
p15 = struct.unpack_from("<I", MEM, SFX_TBL - BASE + 15 * 4)[0]
p36 = struct.unpack_from("<I", MEM, SFX_TBL - BASE + 36 * 4)[0]
print(f"table[15]={hex(p15)} table[36]={hex(p36)}")

# Is 0x4015f0 (bottom play) ever called with these string ptrs as imm?
BOTTOM = 0x4015f0
bcalls = find_calls(BOTTOM)
print(f"\nbottom play calls: {len(bcalls)}")
# check if any push the string addresses
direct_name = []
for c in bcalls:
    ins, idx = decode_window(c, before=0x30)
    if not ins:
        continue
    for i in ins[:idx]:
        if i.mnemonic != "push":
            continue
        if i.operands and i.operands[0].type == CS_OP_IMM:
            imm = i.operands[0].imm
            if imm in (p15, p36, BASE + Z if Z >= 0 else -1, BASE + M if M >= 0 else -1):
                direct_name.append((hex(c), hex(i.address), hex(imm)))
print("bottom calls with ZANSYU/MATISIRO ptr push:", direct_name)

# Final: any place that does push 15 / 36 to a function that eventually calls play_sfx?
# Check 0x47b180 (got push 0xf earlier) - does it call play_sfx?
print("\n=== does 0x47b180 call play_sfx? ===")
for i in md.disasm(rd(0x47b180, 0x80), 0x47b180):
    print(f"{hex(i.address)}: {i.mnemonic} {i.op_str}")
    if i.mnemonic.startswith("ret"):
        break

# Check play_sfx only callee of interest - any movzx from a byte table indexed then call
print("\nDONE")
