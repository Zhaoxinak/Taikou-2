#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe 13: AI selection logic.
1. Disassemble the 4 action-writer functions that set this+0xc (action code):
   0x469480 (->0), 0x4694aa (->di), 0x46950c (->cx, sets 0x5149b0=4), 0x469547 (->5)
2. Find xrefs (e8 rel32) to each writer within the duel module.
3. Disassemble 0x468860 (AI turn) in full to see where this+0xc is seeded.
"""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(r"F:\Games\Taikou 2\scripts\_unpacked_mem.bin", "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def disasm_range(va_start, va_end, label=""):
    """Disassemble [va_start, va_end) and return list of (va, mn, op) lines."""
    out = []
    if label:
        out.append(f"===== {label} [{va_start:#08x} .. {va_end:#08x}] =====")
    for ins in md.disasm(MEM[va_start-BASE:va_end-BASE], va_start):
        out.append(f"  {ins.address:#08x}: {ins.mnemonic} {ins.op_str}")
    return out

def find_xrefs(target, lo=0x460000, hi=0x4c0000):
    """Find e8 rel32 calls whose destination == target within [lo,hi]."""
    hits = []
    for ins in md.disasm(MEM[lo-BASE:hi-BASE], lo):
        if ins.mnemonic != "call":
            continue
        # compute rel32 target
        # call rel32: e8 + imm32; target = ins.address + ins.size + imm
        try:
            disp = int.from_bytes(MEM[ins.address-BASE+1:ins.address-BASE+5], "little", signed=True)
        except Exception:
            continue
        dest = ins.address + ins.size + disp
        if dest == target:
            hits.append(ins.address)
    return sorted(hits)

writers = {
    0x469480: "W0 set this+0xc = 0 (普通攻击?)",
    0x4694aa: "W1 set this+0xc = di",
    0x46950c: "W2 set this+0xc = cx (0x5149b0=4)",
    0x469547: "W3 set this+0xc = 5 (换人/拜托?)",
}

out = []
out.append("############ XREFS to action-writer functions ############")
for va, desc in writers.items():
    xr = find_xrefs(va)
    out.append(f"\n--- xrefs to {va:#08x} ({desc}) ---")
    out.append("  callers: " + (", ".join(f"{x:#08x}" for x in xr) if xr else "NONE"))

out.append("\n\n############ FULL DISASM of writer functions (0x1a0 bytes each) ############")
for va, desc in writers.items():
    out += disasm_range(va, va+0x1a0, f"{desc} @ {va:#08x}")

out.append("\n\n############ FULL DISASM of AI turn 0x468860 (0x400 bytes) ############")
out += disasm_range(0x468860, 0x468c60, "AI turn 0x468860")

open(r"F:\Games\Taikou 2\scripts\_ai7.txt","w",encoding="utf-8").write("\n".join(out))
print("WROTE _ai7.txt")
for va, desc in writers.items():
    xr = find_xrefs(va)
    print(f"xrefs {va:#08x}: {xr if xr else 'NONE'}")
print("done")
