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

for TGT in (0x462460, 0x49b140):
    fs=enclosing(TGT)
    nxt=None
    for f in FUNCS_S:
        if f> TGT-BASE: nxt=f; break
    size=(nxt-(TGT-BASE)) if nxt else 0x1500
    print(f"\n===== 0x{TGT:06x} (fn 0x{fs+BASE:06x}, {size}B) — per-record applier scan =====")
    nins=0
    for ins in disasm(TGT,size):
        nins+=1
        mark=""
        os_=ins.op_str
        if ins.mnemonic.startswith("call"): mark+=" <CALL "+os_+">"
        if ins.mnemonic in ("and","movzx") and "0xff" in os_: mark+=" <<TYPE"
        if ins.mnemonic=="jmp" and ("dword ptr" in os_ or "*4" in os_): mark+=" <<JT-DISPATCH"
        if ins.mnemonic in ("cmp","test") and any(c in os_ for c in ("0x341","833","0xff","0x172")): mark+=" <<CMP"
        if "0x31" in os_ or "0x2f" in os_ or "0x1f" in os_: mark+=" <<STRIDE"
        print(f"  0x{ins.address:06x}: {ins.mnemonic} {os_}{mark}")
        if nins>240:
            print("  ...(truncated 240)")
            break
