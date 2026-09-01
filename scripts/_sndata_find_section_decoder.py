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

SUBS=[0x47d960,0x47dae0,0x47dce0,0x47e130,0x47e3a0,0x47e440,0x47e5a0,0x47e770,
      0x47ea80,0x47ebb0,0x47ecb0,0x47ed10,0x47ed70,0x47ee50,0x47ef00,
      0x47f050,0x47f0a0,0x47f1b0,0x47f210]

# For each sub-decoder: scan its body (find next function start to bound it) for
#  - call 0x47d890 (read_record)
#  - add reg, 0x31  (stride 49 loop)
#  - and ...,0xff   (type byte)
#  - jump-table dispatch (jmp dword ptr [reg*4+imm])
print("sub-decoder | read_record(0x47d890) | stride49(add 0x31) | type&0xff | jmp-dispatch")
results={}
for s in SUBS:
    fs=enclosing(s)
    # bound: next function start after s
    nxt=None
    for f in FUNCS_S:
        if f> s-BASE:
            nxt=f; break
    if nxt is None: nxt= s-BASE+0x2000
    size=nxt-(s-BASE)
    insns=list(md.disasm(code[s-BASE:s-BASE+size], s))
    has_read=any(ins.mnemonic.startswith("call") and ins.op_str==f"0x47d890" for ins in insns)
    has_stride49=any((ins.mnemonic=="add") and ("0x31" in ins.op_str or "49" in ins.op_str) for ins in insns)
    has_typeff=any((ins.mnemonic in("and","movzx")) and "0xff" in ins.op_str for ins in insns)
    has_dispatch=any(ins.mnemonic=="jmp" and ("dword ptr" in ins.op_str or "*4" in ins.op_str) for ins in insns)
    results[s]=dict(read=has_read,stride49=has_stride49,typeff=has_typeff,dispatch=has_dispatch,nbytes=size,nins=len(insns))
    print(f"  0x{s:06x} | {str(has_read):5} | {str(has_stride49):5} | {str(has_typeff):5} | {str(has_dispatch):5}  ({size}B,{len(insns)}ins)")

# Also: who calls 0x47d890 across the whole image?
print("\n===== all call sites of read_record 0x47d890 =====")
allsites=[]
i=code.find(b'\xe8')
# find rel32 calls: pattern \xe8 + rel32
import re
pat=re.compile(b'\xe8([\x00-\xff]{3}\xff)' if False else b'\xe8....')
off=0
while True:
    idx=code.find(b'\xe8', off)
    if idx<0: break
    rel=struct.unpack("<i", code[idx+1:idx+5])[0]
    tgt=BASE+idx+5+rel
    if tgt==0x47d890:
        allsites.append(BASE+idx)
    off=idx+1
print(f"  total {len(allsites)} call sites")
for a in allsites:
    print(f"    0x{a:06x}  in fn 0x{enclosing(a)+BASE:06x}")
