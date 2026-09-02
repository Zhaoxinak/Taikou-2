#!/usr/bin/env python3
# 续233: in 伪兵 handler (0x435570..), find what esi holds at call 0x43568c -> 0x43a440.
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BASE=0x400000
MEM=open("/Users/ts/Downloads/Taikou 2/scripts/_unpacked_mem.bin","rb").read()
def read(va,n): return MEM[va-BASE:va-BASE+n]
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True

def dis(va, nbytes, stop_at=None):
    out=[]
    for ins in md.disasm(read(va, nbytes), va):
        out.append(ins)
        if stop_at is not None and ins.address>=stop_at:
            break
    return out

print("=== 伪兵 handler 0x435570 .. call 0x43568c ===")
for ins in dis(0x435570, 0x43568c-0x435570+12):
    s="0x%06x %-10s %s"%(ins.address, ins.mnemonic, ins.op_str)
    # highlight esi writes / tactic id loads
    if 'esi' in ins.op_str or 'eax' in ins.op_str:
        s+="   <=="
    print(s)
