from capstone import Cs, CS_ARCH_X86, CS_MODE_32
DATA = open('_unpacked_mem.bin','rb').read()
BASE = 0x400000
cs = Cs(CS_ARCH_X86, CS_MODE_32)
def disasm(va, nbytes):
    return list(cs.disasm(DATA[va-BASE:va-BASE+nbytes], va))
def show(name, va, nbytes):
    print(f"\n===== {name} @0x{va:06x} =====")
    for ins in disasm(va, nbytes):
        print(f"  0x{ins.address:06x}: {ins.mnemonic} {ins.op_str}")
show("A-hdr reader 0x439060", 0x439060, 0xb0)
show("stride-8 fn 0x439130", 0x439130, 0xc0)
