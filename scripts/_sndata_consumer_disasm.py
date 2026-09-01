import os, struct, pickle
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE=0x400000
code=open("scripts/_unpacked_mem.bin","rb").read()
insn=pickle.load(open("scripts/_insn_addrs.pkl","rb"))
FUNCS=sorted(insn[1])  # function starts in FILE-OFFSET units

def enclosing_func(off):
    lo,hi=0,len(FUNCS)-1;ans=None
    while lo<=hi:
        m=(lo+hi)//2
        if FUNCS[m]<=off: ans=FUNCS[m]; lo=m+1
        else: hi=m-1
    return ans

def find_refs(target):
    pat=struct.pack("<I",target)
    out=[]; i=code.find(pat)
    while i!=-1:
        out.append(i); i=code.find(pat,i+1)
    return out

targets={0x522c88:"VIEW0(43B)",0x522c60:"VIEW1(30B)",0x522c70:"VIEW2(17B)"}
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
seen=set()
for t,name in targets.items():
    rs=find_refs(t)
    funcs=set()
    for off in rs:
        f=enclosing_func(off)
        if f: funcs.add(f)
    print(f"0x{t:06x} {name}: {len(rs)} refs @ fileoffs {[hex(x) for x in rs]} in fns {[hex(BASE+f) for f in sorted(funcs)]}")
    for f in sorted(funcs):
        if f in seen: continue
        seen.add(f)
        blob=code[f:f+400]
        print(f"\n===== FUNCTION 0x{BASE+f:06x} (consumer of {name}) =====")
        n=0
        for ins in md.disasm(blob,BASE+f):
            mark=""
            for tt in targets:
                if struct.pack("<I",tt) in ins.bytes:
                    mark=f"  <<< 0x{tt:06x}"
            print(f"  0x{ins.address:06x}: {ins.mnemonic} {ins.op_str}{mark}")
            n+=1
            if n>90: break
