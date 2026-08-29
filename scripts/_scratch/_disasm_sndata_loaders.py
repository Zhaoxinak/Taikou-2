import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = "_unpacked_mem.bin"
base = 0x400000
mem = open(MEM, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)

def disasm(start, end, label, out):
    out.append("========== %s  (0x%x - 0x%x) ==========" % (label, start, end))
    try:
        code = mem[start-base:end-base]
    except Exception as e:
        out.append("  ERROR slice: %s" % e)
        return
    for ins in md.disasm(code, start):
        if ins.address > end:
            break
        # resolve immediate refs to known globals
        op = ins.op_str
        out.append("%08x  %-10s %s" % (ins.address, ins.mnemonic, op))

ranges = [
    (0x47d720, 0x47d860, "LoadSNDATA @0x47d720"),
    (0x47d860, 0x47de00, "40960-block accessor @0x47d860"),
]
out = []
for s,e,l in ranges:
    disasm(s,e,l,out)
open("_sndata_loaders_a.asm","w").write("\n".join(out))
print("wrote _sndata_loaders_a.asm  lines=%d" % len(out))
