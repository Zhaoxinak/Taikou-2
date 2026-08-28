import struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DATA = open('_unpacked_mem.bin','rb').read()
BASE = 0x400000
cs = Cs(CS_ARCH_X86, CS_MODE_32)
cs.detail = True

def disasm(va, nbytes):
    o = va - BASE
    code = DATA[o:o+nbytes]
    out = []
    for ins in cs.disasm(code, va):
        out.append(ins)
    return out

def hexstr(b):
    return b.hex()

UNIT = 0x512b60
TERR = 0x512868

# Disassemble the deployment/unit region and tag every instruction that
# references either buffer, and show index-math (imul / lea with *40,*19,*760).
lo, hi = 0x438b00, 0x439780
insns = disasm(lo, hi - lo)
print(f"=== region 0x{lo:06x}..0x{hi:06x} ({len(insns)} insns) ===")
for ins in insns:
    s = ins
    op = ins.op_str or ""
    marker = ""
    if "0x512b60" in op or "0x512868" in op:
        marker = "  <<< BUF"
    # detect index scaling
    if ins.mnemonic in ("imul","mul"):
        marker += "  [MUL]"
    if "0x28" in op or "0x13" in op or "0x2f8" in op or "0x14" in op or "0x19" in op:
        marker += "  [SCALE]"
    if ins.mnemonic == "call":
        marker += "  <CALL>"
    if marker:
        print(f"  0x{ins.address:06x}: {ins.mnemonic} {op}{marker}")
