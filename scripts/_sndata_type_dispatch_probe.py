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

def dump(va, label):
    fs=enclosing(va)
    # bound to next func
    nxt=None
    for f in FUNCS_S:
        if f > va-BASE: nxt=f; break
    size=(nxt-(va-BASE)) if nxt else 0x800
    print(f"\n===== {label}: 0x{va:06x} (fn 0x{fs+BASE:06x}, {size}B) =====")
    cur_type=None
    for ins in disasm(va, size):
        mark=""
        os_=ins.op_str
        if ins.mnemonic.startswith("call"): mark+=" <CALL "+os_+">"
        if "0x5" in os_ and ":" not in os_ and ("ptr" in os_ or os_.startswith("0x5")): mark+=" <<G"
        if ins.mnemonic in ("and","movzx") and "0xff" in os_: mark+=" <<TYPE-BYTE"
        if "0x31" in os_ or "49" in os_: mark+=" <<49"
        if ins.mnemonic in ("cmp","test") and "0x341" in os_: mark+=" <<CMP833"
        print(f"  0x{ins.address:06x}: {ins.mnemonic} {os_}{mark}")

dump(0x47dce0, "RECORD CONSUMER A 0x47dce0")
dump(0x47e130, "RECORD CONSUMER B 0x47e130")
