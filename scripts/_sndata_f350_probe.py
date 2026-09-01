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

PROD=0x47f350
fs=enclosing(PROD)
print(f"0x{PROD:06x} enclosing fn start = 0x{fs+BASE:06x}")
# Disassemble a large chunk; look for type dispatch
N=6000
insns=disasm(PROD,N)
print(f"===== 0x{PROD:06x} (bulk decoder / 18 sub-decoders?) — {len(insns)} insns / {N}B =====")
call_targets=set()
for ins in insns:
    mark=""
    os_=ins.op_str
    if ins.mnemonic.startswith("call"):
        # record unique call targets
        try:
            t=int(os_,16)
            call_targets.add(t)
        except: pass
        mark=" <CALL "+os_+">"
    if "0x522c" in os_: mark+=" <<VIEW"
    if "0x50d" in os_ or "0x520" in os_: mark+=" <<GLOBAL"
    # highlight the type byte read: and ...,0xff ; or movzx
    if "0xff" in os_ and (ins.mnemonic in ("and","movzx")): mark+=" <<TYPE-BYTE?"
    # jump tables / dispatch
    if ins.mnemonic in ("jmp","call") and ("dword ptr" in os_ or "eax*4" in os_): mark+=" <<DISPATCH"
    print(f"  0x{ins.address:06x}: {ins.mnemonic} {os_}{mark}")

print("\n===== unique CALL targets (candidate sub-decoders) =====")
for t in sorted(call_targets):
    print(f"  0x{t:06x}  (fn start 0x{enclosing(t)+BASE:06x})")
