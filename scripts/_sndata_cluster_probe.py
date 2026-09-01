import os, struct, pickle
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BASE=0x400000
code=open("scripts/_unpacked_mem.bin","rb").read()
pkl=pickle.load(open("scripts/_insn_addrs.pkl","rb"))
FUNCS_S=sorted(pkl[1])
def enclosing(va):
    fo=va-BASE; lo,hi=0,len(FUNCS_S)-1; best=None
    while lo<=hi:
        m=(lo+hi)//2
        if FUNCS_S[m]<=fo: best=FUNCS_S[m]; lo=m+1
        else: hi=m-1
    return best
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
def disasm(va,n):
    fo=va-BASE
    return list(md.disasm(code[fo:fo+n],va))
def dump(va, n, label, hi_global=True, hi_stack=True, hi_call=True):
    fs=enclosing(va)
    print(f"\n===== {label}: 0x{va:06x} (fn start 0x{fs+BASE:06x}) — {n} bytes =====")
    for ins in disasm(va,n):
        mark=""
        os_=ins.op_str
        if hi_call and ins.mnemonic.startswith("call"): mark+=" <CALL "+os_+">"
        if hi_global and "0x5" in os_ and ":" not in os_: mark+=" <<GLOBAL"
        if hi_stack and ("esp" in os_ or "ebp" in os_): mark+=" <<STACK"
        print(f"  0x{ins.address:06x}: {ins.mnemonic} {os_}{mark}")

# 1) The producer: where does 0x47fc60 sink the full 49B record?
dump(0x47fc60, 900, "PRODUCER 0x47fc60 (full-record sink?)")
# 2) MODE-0 lead handler (called in 0x4e8600 / 0x488290 MODE==0 branch)
dump(0x492e20, 1400, "CONSUMER MODE0 lead 0x492e20")
# 3) MODE-2+ lead handler (0x4e8600 else branch)
dump(0x491e70, 1400, "CONSUMER MODE2+ lead 0x491e70")
