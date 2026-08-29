"""Resolve the indirect finalize call [0x4fb09c] and the GDI palette imports,
then disassemble the finalize fn to find how the 8bpp object gets its palette."""
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x400000
data = open("_unpacked_mem.bin", "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def ro(va, n):  # read bytes at VA
    return data[va-BASE: va-BASE+n]
def r32(va):
    return struct.unpack("<I", ro(va, 4))[0]
def off_of(va): return va - BASE

# 1) Resolve [0x4fb09c]
fnptr = r32(0x4fb09c)
print(f"[0x4fb09c] -> finalize fn @0x{fnptr:06x}")

# 2) Parse PE import table to map IAT thunks -> function names.
#    DOS hdr at 0x400000; e_lfanew at 0x3c.
e_lfanew = r32(0x400000 + 0x3c)
print(f"e_lfanew = 0x{e_lfanew:06x}")
pe = BASE + e_lfanew
# PE sig(4) + COFF hdr(20) + Optional hdr. DataDirectory at offset 96 in optional hdr (for PE32).
# Optional header starts at pe+24. Import table dir is index 1, at pe+24+96 = pe+120.
imp_rva = r32(pe + 24 + 96)      # Import Table RVA
imp_size = r32(pe + 24 + 96 + 4)
print(f"Import Table RVA=0x{imp_rva:06x} size=0x{imp_size:x}")

# walk import descriptors (20 bytes each) until all-zero
def name_at(rva):
    o = rva - BASE
    s = b""
    while data[o] != 0:
        s += bytes([data[o]]); o += 1
    return s.decode("latin1", "replace")

GDI_FUNCS = {}
o = imp_rva
while True:
    desc = data[o-BASE: o-BASE+20]
    if desc == b"\x00"*20:
        break
    origfirstthunk, timestamp, fwd, name_rva, firstthunk = struct.unpack("<IIIII", desc)
    dll = name_at(name_rva)
    # thunks: use OriginalFirstThunk (INT) if present else FirstThunk
    th = origfirstthunk if origfirstthunk else firstthunk
    while True:
        t = r32(th)
        if t == 0:
            break
        if t & 0x80000000:
            fname = f"ord{t & 0x7fff}"
        else:
            fname = name_at(t + 2)  # hint(2)+name
        GDI_FUNCS[firstthunk] = (dll, fname)
        th += 4
    o += 20

print("\n=== GDI/bitmap-related imports ===")
for thunk, (dll, fname) in sorted(GDI_FUNCS.items()):
    fu = fname.upper()
    if any(k in fu for k in ["DIB","PALETTE","BITBLT","STRETCH","BITMAP","GETPIXEL","SETPIXEL","CREATECOMPAT","SELECTOBJECT","GETDC"]):
        print(f"  IAT@0x{thunk:06x}  {dll}:{fname}")

# 3) Disassemble the finalize fn
def disasm(va, n):
    chunk = data[off_of(va): off_of(va)+n]
    return [ins for ins in md.disasm(chunk, va)]

print(f"\n================ FINALIZE fn @0x{fnptr:06x} ================")
for ins in disasm(fnptr, 0x300):
    s = f"0x{ins.address:06x}: {ins.mnemonic} {ins.op_str}"
    # flag GDI calls and object-space ptrs
    op = ins.op_str
    flag = ""
    if ins.mnemonic == "call":
        # resolve direct call target name if it's an import thunk?
        flag = "  <CALL>"
    if "0x52" in op or "0x51" in op:
        flag += "  [obj]"
    print(s + flag)
