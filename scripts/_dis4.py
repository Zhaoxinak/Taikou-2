from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import *
IMG = open('scripts/_unpacked_mem.bin','rb').read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

def dis(va, nbytes):
    off = va - BASE
    print(f"\n===== func 0x{va:x} =====")
    for ins in md.disasm(IMG[off:off+nbytes], va):
        print(f"0x{ins.address:x}  " + ins.mnemonic + "  " + ins.op_str)
        if ins.mnemonic in ('ret','retn'): break

dis(0x47da10, 96)
dis(0x47da50, 96)
dis(0x47d960, 128)
