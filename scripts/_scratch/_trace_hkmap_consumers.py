"""Trace consumers of the HKMAP/HJMAP object (0x524990) to find the palette.

We know:
  - 0x433780  = generic LZW->object loader (fills object buffers)
  - 0x524990  = HKMAP/HJMAP decoded pixel object
  - 0x524918  = HJCHAR decoded pixel object
  - 0x5249c0  = HGRP  decoded pixel object
  - 0x524978  = scratch buffer in the loader (NOT the real data)

Goal: find where 0x524990 is *consumed* (render path) and how a color
palette is attached, so we can produce true-color atlases.
"""
import struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x400000
data = open("_unpacked_mem.bin", "rb").read()
SIZE = len(data)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

# Object VAs to trace.
TARGETS = {
    0x524990: "HKMAP/HJMAP",
    0x524918: "HJCHAR",
    0x5249c0: "HGRP",
}

def va_of(off): return off + BASE
def off_of(va): return va - BASE

def find_immediate_refs(va):
    """Find `mov reg, 0xVA` (and similar) immediate references."""
    pats = []
    for opc in (0xb8, 0xb9, 0xba, 0xbb, 0xbc, 0xbd, 0xbe, 0xbf):  # mov r32, imm32
        pats.append(bytes([opc]) + struct.pack("<I", va))
    hits = []
    for p in pats:
        start = 0
        while True:
            i = data.find(p, start)
            if i < 0:
                break
            hits.append(va_of(i))
            start = i + 1
    return sorted(set(hits))

def find_disp_refs(va):
    """Find memory operands referencing [0xVA] or [reg+0xVA]."""
    hits = []
    # disp32 form: ModRM with mod=00, rm=101 -> disp32 follows
    # We'll just scan for the 4-byte LE value as part of a ModRM disp
    pat = struct.pack("<I", va)
    start = 0
    while True:
        i = data.find(pat, start)
        if i < 0:
            break
        # check preceding byte could be a ModRM with disp32
        if i >= 1:
            hits.append(va_of(i))
        start = i + 1
    return sorted(set(hits))

def func_start(va):
    """Scan backwards for a function prologue."""
    off = off_of(va)
    lo = max(0, off - 0x2000)
    # prologues:
    #  push ebp / mov ebp, esp       55 89 E5
    #  mov ebp, ecx                 89 CD  (thiscall, no ebp)
    #  sub esp, imm                 81 EC .. .. .. ..
    best = off
    for i in range(off, lo, -1):
        if data[i] == 0x55 and i + 1 < SIZE and data[i+1] == 0x89 and data[i+2] == 0xE5:
            return va_of(i)
        if data[i] == 0x89 and i + 1 < SIZE and data[i+1] == 0xCD:
            return va_of(i)
        if data[i] == 0x81 and i + 1 < SIZE and data[i+1] == 0xEC:
            return va_of(i)
    return va  # give up, use the ref itself

def disasm(va_start, va_end):
    off0 = off_of(va_start)
    off1 = off_of(va_end)
    chunk = data[off0:off1]
    out = []
    for ins in md.disasm(chunk, va_start):
        out.append(ins)
    return out

# GDI palette-related imports (will match by mnemonic/operand heuristics)
PALETTE_HINTS = ["CreateDIBSection", "SetDIBColorTable", "StretchDIBits",
                 "SetDIBitsToDevice", "CreateDIBitmap", "BitBlt",
                 "GetDIBits", "CreatePalette", "SetDIBits"]

def main():
    for va, label in TARGETS.items():
        refs = find_immediate_refs(va)
        drefs = find_disp_refs(va)
        print(f"\n================ {label} @0x{va:06x} ================")
        print(f"  immediate refs ({len(refs)}): {[hex(r) for r in refs[:20]]}")
        print(f"  disp refs     ({len(drefs)}): {[hex(r) for r in drefs[:20]]}")
        # Disassemble a window around each immediate ref (the object ptr is
        # loaded into a register there, then fields are read for drawing).
        MAXW = 40
        for idx, r in enumerate(refs[:MAXW]):
            wlo = max(BASE, r - 0x50)
            whi = r + 0x130
            insns = disasm(wlo, whi)
            print(f"\n  --- window @ref 0x{r:06x} (win 0x{wlo:06x}..0x{whi:06x}) ---")
            for ins in insns:
                s = f"    0x{ins.address:06x}: {ins.mnemonic} {ins.op_str}"
                flag = ""
                if ins.mnemonic == "call":
                    flag = "  <-- CALL"
                op = ins.op_str
                # highlight object-space reads/writes (0x51xxxx/0x52xxxx)
                if "0x52" in op or "0x51" in op:
                    flag += "  [obj]"
                print(s + flag)

if __name__ == "__main__":
    main()
