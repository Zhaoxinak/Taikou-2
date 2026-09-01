import os, struct, pickle
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BASE=0x400000
code=open("scripts/_unpacked_mem.bin","rb").read()
pkl=pickle.load(open("scripts/_insn_addrs.pkl","rb"))
FUNCS=pkl[1]  # list of function-start FILE OFFSETS
FUNCS_S=sorted(FUNCS)
def enclosing_func_off(va):
    fo=va-BASE
    # binary search for largest FUNCS_S <= fo
    lo,hi=0,len(FUNCS_S)-1
    best=None
    while lo<=hi:
        mid=(lo+hi)//2
        if FUNCS_S[mid]<=fo:
            best=FUNCS_S[mid]; lo=mid+1
        else:
            hi=mid-1
    return best
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
def disasm(va, n):
    fo=va-BASE
    return list(md.disasm(code[fo:fo+n], va))

caller_va=0x488290
fstart=enclosing_func_off(caller_va)
print(f"0x{caller_va:06x} enclosing function start (file off) = 0x{fstart:x}  -> VA 0x{fstart+BASE:06x}")
# disassemble from function start, generous length to capture the whole function
N=2200
insns=disasm(fstart+BASE, N)
print(f"===== 0x{fstart+BASE:06x} (caller 0x47fc60 @0x4882b1) — {len(insns)} insns, {N} bytes =====")
for ins in insns:
    mark=""
    os_=ins.op_str
    if ins.mnemonic.startswith("call"):
        mark=" <CALL "+os_+">"
    # flag reads/writes of the 3 view globals (structured consumer candidate)
    if "0x522c" in os_: mark+=" <<VIEW-GLOBAL"
    # flag reads of a local buffer that could be the record (mov ...,[esp+...] right after read)
    if "esp" in os_ or "ebp" in os_: mark+=" <<STACK"
    if ins.address==0x4882b1: mark+="  <== CALL 0x47fc60"
    print(f"  0x{ins.address:06x}: {ins.mnemonic} {os_}{mark}")
