import os, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BASE=0x400000
code=open("scripts/_unpacked_mem.bin","rb").read()
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True

def disasm(va, n):
    fo=va-BASE
    return list(md.disasm(code[fo:fo+n], va))

print("===== 0x4e8600 (main loop / record processor) — 2600 bytes =====")
insns=disasm(0x4e8600, 2600)
for ins in insns:
    mark=""
    if "0x522c" in ins.op_str: mark=" <<VIEW"
    if ins.mnemonic.startswith("call"):
        mark+=" <CALL "+ins.op_str+">"
    # flag reads of a local buffer that could be the record (mov ...,[esp+...] right after read)
    print(f"  0x{ins.address:06x}: {ins.mnemonic} {ins.op_str}{mark}")
