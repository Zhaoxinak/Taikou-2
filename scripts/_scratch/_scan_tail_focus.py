# -*- coding: utf-8 -*-
"""Focused evidence: callers, loader mapping, reliable entity reads."""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
import struct, collections, os, json

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
ROOT = os.path.dirname(SCRIPTS)
BASE = 0x400000
mem = open(os.path.join(SCRIPTS, "_unpacked_mem.bin"), "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)

def dis(va, n=0x60):
    out = []
    for ins in md.disasm(mem[va-BASE:va-BASE+n], va):
        out.append(ins)
        if ins.mnemonic.startswith("ret") and len(out) > 3:
            break
    return out

def count_calls(target):
    c, addrs = 0, []
    for off in range(0x1000, 0xF0000 - 5):
        if mem[off] != 0xE8:
            continue
        rel = struct.unpack_from("<i", mem, off + 1)[0]
        if BASE + off + 5 + rel == target:
            c += 1
            addrs.append(BASE + off)
    return c, addrs

def context(va, before=0x30, after=0x50):
    print(f"\n---- context @{va:#x} ----")
    start = va - before
    for ins in md.disasm(mem[start-BASE:va-BASE+after], start):
        mark = ">>" if ins.address == va else "  "
        print(f"{mark}{ins.address:#x}: {ins.mnemonic:8} {ins.op_str}")
        if ins.address > va + after - 0x10 and ins.mnemonic.startswith("ret"):
            break

# ---- 1. Setter cluster ----
print("===== SETTER DISASM =====")
for ea in [0x49A630, 0x49A640, 0x49A650, 0x49A670, 0x49A690,
           0x49AB80, 0x49ABA0, 0x49ABC0, 0x49ABE0, 0x49AC00, 0x49AC30]:
    print(f"\n### {ea:#x}")
    for ins in dis(ea, 0x30):
        print(f"  {ins.address:#x}: {ins.mnemonic:8} {ins.op_str}")

# Find function starts in 0x49a5xx..0x49a7xx by scanning for ret-aligned
print("\n===== 0x49a500..0x49a800 function map =====")
for va in range(0x49a500, 0x49a800, 0x10):
    # if looks like start
    prev = mem[va-BASE-1]
    if prev not in (0xC3, 0xCC) and not (prev == 0x00 and mem[va-BASE-2] in (0xC2, 0xC3)):
        # also accept after ret imm16 (C2 xx xx)
        if not (mem[va-BASE-3] == 0xC2):
            continue
    for ins in dis(va, 0x28):
        if "+ 0x1" in ins.op_str or "+ 0x2" in ins.op_str:
            print(f"  {va:#x}: touches {ins.mnemonic} {ins.op_str}")
            break

# ---- 2. Callers of key setters ----
print("\n===== CALLERS + nearby push args =====")
for target, name in [
    (0x49A650, "set_max_stamina/+0x20"),
    (0x49A640, "set_+0x21"),
    (0x49AC00, "set_+0x1d"),
    (0x49AC30, "set_+0x1e"),
    (0x49ABE0, "+0x1c|=0x20"),
    (0x49ABC0, "+0x1c|=0x10"),
    (0x49ABA0, "+0x1c|=0x08"),
    (0x49AB80, "+0x1c|=0x04"),
]:
    c, addrs = count_calls(target)
    print(f"\n## {target:#x} {name}: {c} calls")
    for a in addrs[:15]:
        # show preceding instructions for push args
        print(f"  call@{a:#x}:")
        for ins in md.disasm(mem[a-0x20-BASE:a+5-BASE], a-0x20):
            mark = ">>" if ins.address == a else "  "
            print(f"  {mark}{ins.address:#x}: {ins.mnemonic:8} {ins.op_str}")

# ---- 3. Reliable entity consumers (known from docs / cmp 0xff patterns) ----
print("\n===== KNOWN CONSUMER SITES =====")
for va in [0x44426d, 0x49e576, 0x4aa3ad, 0x4ab56b, 0x447992,
           0x410ddc, 0x4634f9, 0x460579, 0x47e074, 0x47e07f,
           0x4453a0, 0x44d50b, 0x452fc2, 0x4a7023, 0x4ab530,
           0x46b313, 0x49cf47, 0x4a3e74]:
    context(va, before=0x40, after=0x40)

# ---- 4. BSDATA loader copy path ----
print("\n===== loader / remap evidence around 0x47df76 / 0x47f7b0 =====")
for va in [0x47df50, 0x47f7b0, 0x47de40]:
    print(f"\n### {va:#x}")
    for ins in dis(va, 0xA0):
        print(f"  {ins.address:#x}: {ins.mnemonic:8} {ins.op_str}")
