import os, struct, pickle
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BASE=0x400000
code=open("scripts/_unpacked_mem.bin","rb").read()
pkl=pickle.load(open("scripts/_insn_addrs.pkl","rb"))
FUNCS_S=sorted(pkl[1])
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
def disasm(va,n):
    fo=va-BASE
    return list(md.disasm(code[fo:fo+n],va))

# Definitive: any function that pushes 0x31 (49) then calls 0x4411b0 (file-read) = reads 49B records.
# Also report push 0x2f(47)/0x1f(31) -> call 0x4411b0 = entity/city decoders.
print("fn | reads49(push 0x31->call 0x4411b0) | reads47(push 0x2f) | reads31(push 0x1f)")
hits49=[]; hits47=[]; hits31=[]
for f in FUNCS_S:
    va=BASE+f
    if va < 0x400000 or va > 0x500000: continue
    insns=disasm(va, 0x1000)
    if not insns: continue
    # find call 0x4411b0 with preceding push 0x31/0x2f/0x1f within 6 insns
    for i,ins in enumerate(insns):
        if ins.mnemonic.startswith("call") and ins.op_str=="0x4411b0":
            # look back up to 6
            for j in range(max(0,i-6), i):
                p=insns[j]
                if p.mnemonic=="push" and p.op_str in ("0x31","0x2f","0x1f"):
                    if p.op_str=="0x31": hits49.append(va)
                    elif p.op_str=="0x2f": hits47.append(va)
                    elif p.op_str=="0x1f": hits31.append(va)
                    break

def show(label, hits):
    uniq=sorted(set(hits))
    print(f"  {label}: {len(uniq)} funcs -> " + ", ".join(f"0x{v:06x}" for v in uniq) if uniq else f"  {label}: NONE")
print("===== functions reading fixed-size records via 0x4411b0 =====")
show("reads49(stride49 SNDATA)", hits49)
show("reads47(stride47 entity)", hits47)
show("reads31(stride31 city)", hits31)

# Also: find loops bounded by 833 (0x341) anywhere in code
print("\n===== loops bounded by cmp ...,0x341 (833 records) =====")
found=[]
for f in FUNCS_S:
    va=BASE+f
    if va<0x400000 or va>0x500000: continue
    insns=disasm(va,0x1000)
    for ins in insns:
        if ins.mnemonic=="cmp" and ("0x341" in ins.op_str or "833" in ins.op_str):
            found.append(va); break
for v in sorted(set(found)):
    print(f"  0x{v:06x}")
if not found: print("  NONE")
