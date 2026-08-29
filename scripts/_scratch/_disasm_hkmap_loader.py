#!/usr/bin/env python3
# Disassemble the core file->object loader 0x433780 and the HKMAP/HJMAP
# init chain to recover battle-tile pixel layout (bpp, tile dims, palette).
import struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x400000
data = open(r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin", "rb").read()

def disasm(va_start, va_end):
    off = va_start - BASE
    chunk = data[off:(va_end - BASE)]
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    out = []
    for ins in md.disasm(chunk, va_start):
        out.append((ins.address, ins.mnemonic, ins.op_str))
    return out

# Loader 0x433780 (called with: file_str, obj_ptr, size, flag)
print("="*70)
print("CORE LOADER 0x433780  (window 0x433780..0x433860)")
print("="*70)
for a, m, o in disasm(0x433780, 0x433860):
    print(f"  0x{a:06x}: {m} {o}")

# The init chain entry (0x43385b region) — already seen; disassemble the
# 0x433930..0x433a40 tail which chooses variant & loads HKMAPNEW etc.
print()
print("="*70)
print("INIT TAIL 0x4339c0..0x433a40 (variant select + loaders)")
print("="*70)
for a, m, o in disasm(0x4339c0, 0x433a40):
    print(f"  0x{a:06x}: {m} {o}")

# 0x43a460 and 0x43a580 (HKMAPNEW / HJMAPDAT-ish loaders referenced)
for fn, lo, hi in [("0x43a460",0x43a460,0x43a500),("0x43a580",0x43a580,0x43a640)]:
    print()
    print("="*70)
    print(f"LOADER {fn}  window 0x{lo:06x}..0x{hi:06x}")
    print("="*70)
    for a, m, o in disasm(lo, hi):
        print(f"  0x{a:06x}: {m} {o}")
