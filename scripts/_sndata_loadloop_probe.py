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

SUBS=[0x47d960,0x47dae0,0x47dce0,0x47e130,0x47e3a0,0x47e440,0x47e5a0,0x47e770,
      0x47ea80,0x47ebb0,0x47ecb0,0x47ed10,0x47ed70,0x47ee50,0x47ef00,
      0x47f050,0x47f0a0,0x47f1b0,0x47f210]

# Signature of idx*49+0x10  (same as read_record 0x47d890):
#   lea reg,[reg+reg*2]  (idx*3)   -> mnemonic lea, op_str has '*2'
#   shl reg, 4           (idx*48)
#   lea reg,[...+reg+0x10] (idx*49+0x10)  -> op_str has '0x10' and '+'
def has_idx49(insns):
    has_lea2=False; has_shl4=False; has_plus10=False; has_cmp833=False
    for ins in insns:
        os_=ins.op_str
        if ins.mnemonic=="lea" and "*2" in os_: has_lea2=True
        if ins.mnemonic=="shl" and "4" in os_: has_shl4=True
        if ins.mnemonic=="lea" and "0x10" in os_: has_plus10=True
        if ins.mnemonic=="cmp" and any(x in os_ for x in ("0x341","0x342","0x340","833","834")): has_cmp833=True
    return has_lea2,has_shl4,has_plus10,has_cmp833

print("sub | lea*2 | shl4 | +0x10 | cmp833 | note")
for s in SUBS:
    nxt=None
    for f in FUNCS_S:
        if f> s-BASE: nxt=f; break
    size=(nxt-(s-BASE)) if nxt else 0x2000
    insns=disasm(s,size)
    a,b,c,d=has_idx49(insns)
    # also detect load of blob base: mov eax,[esi] or mov eax,[ecx]
    loadbase=any(ins.mnemonic=="mov" and ("[esi]" in ins.op_str or "[ecx]" in ins.op_str) and "eax" in ins.op_str.split(",")[0] for ins in insns)
    print(f"  0x{s:06x} | {str(a):5} | {str(b):5} | {str(c):5} | {str(d):5} | base=[esi]/[ecx]?{loadbase}")

# Also whole-image: find every function that contains BOTH lea*2 AND shl 4 AND +0x10 (the idx*49 idiom)
# = every place that iterates/computes record offsets.
print("\n===== whole-image functions containing idx*49+0x10 idiom (record iterators/consumers) =====")
found=[]
for f in FUNCS_S:
    va=BASE+f
    if f < 0x47d000 or f > 0x4a0000:  # bound scan to code of interest
        continue
    insns=disasm(va, 0x800)
    if not insns: continue
    a,b,c,_=has_idx49(insns)
    if a and b and c:
        found.append(va)
for va in found:
    print(f"  0x{va:06x}")
