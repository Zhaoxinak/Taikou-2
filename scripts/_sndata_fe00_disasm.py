import os, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BASE=0x400000
code=open("scripts/_unpacked_mem.bin","rb").read()
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True

def disasm(va, n):
    fo=va-BASE
    return list(md.disasm(code[fo:fo+n], va))

# 0x47fe00 record iterator
print("===== 0x47fe00 (record iterator) — first 1200 bytes =====")
insns=disasm(0x47fe00, 1200)
for ins in insns:
    mark=""
    if "0x522c" in ins.op_str: mark=" <<VIEW"
    if ins.mnemonic.startswith("call"): mark+=" <CALL>"
    print(f"  0x{ins.address:06x}: {ins.mnemonic} {ins.op_str}{mark}")
