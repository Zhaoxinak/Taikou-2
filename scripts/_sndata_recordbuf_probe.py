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

print("===== read_record 0x47d890 (find source buffer base) =====")
for ins in disasm(0x47d890, 220):
    mark=""
    if "0x5" in ins.op_str and ":" not in ins.op_str: mark=" <<GLOBAL"
    if ins.mnemonic.startswith("call"): mark+=" <CALL "+ins.op_str+">"
    if "0x31" in ins.op_str or "49" in ins.op_str: mark+=" <<STRIDE49?"
    print(f"  0x{ins.address:06x}: {ins.mnemonic} {ins.op_str}{mark}")
    if ins.mnemonic=="ret": break

# Now find which of the 19 subs WRITE to that base. We'll search each sub for 'mov ... ,reg' into a global.
# First, collect global-store targets per sub.
SUBS=[0x47d960,0x47dae0,0x47dce0,0x47e130,0x47e3a0,0x47e440,0x47e5a0,0x47e770,
      0x47ea80,0x47ebb0,0x47ecb0,0x47ed10,0x47ed70,0x47ee50,0x47ef00,
      0x47f050,0x47f0a0,0x47f1b0,0x47f210]
print("\n===== per-sub: store-to-global (dword ptr [0x5xxxxx], reg) and imul/lea scales =====")
for s in SUBS:
    nxt=None
    for f in FUNCS_S:
        if f > s-BASE: nxt=f; break
    size=(nxt-(s-BASE)) if nxt else 0x2000
    insns=disasm(s,size)
    gstores=set()
    scales=set()
    for ins in insns:
        os_=ins.op_str
        if ins.mnemonic in ("mov","movzx","movsx") and "dword ptr [0x5" in os_ and "," in os_:
            # [0x5.....], reg
            dst=os_.split(",")[0].strip()
            gstores.add(dst)
        if ins.mnemonic in ("imul","lea") and ("0x31" in os_ or "*4" in os_ or "0x2e" in os_ or "0x2f" in os_):
            scales.add(os_)
    print(f"  0x{s:06x}: globals_stored={sorted(gstores)[:6]}{'...' if len(gstores)>6 else ''}  scales={sorted(scales)[:4]}")
