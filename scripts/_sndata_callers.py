import os, struct, pickle
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BASE=0x400000
code=open("scripts/_unpacked_mem.bin","rb").read()
FUNCS=sorted(pickle.load(open("scripts/_insn_addrs.pkl","rb"))[1])
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True

def enclosing(off):
    lo,hi=0,len(FUNCS)-1;ans=None
    while lo<=hi:
        m=(lo+hi)//2
        if FUNCS[m]<=off: ans=FUNCS[m]; lo=m+1
        else: hi=m-1
    return ans

def find_calls(target):
    # find `call 0x47fc60` / `call 0x47ff50` byte pattern: e8 + rel32
    rel=struct.pack("<i", (target-(BASE+ (code.find(b'\xe8\x00\x00\x00\x00') if False else 0))) )  # placeholder
    out=[]
    # scan all code for e8 + rel to target
    pat_prefix=b"\xe8"
    i=code.find(pat_prefix)
    while i!=-1:
        if i+5<=len(code):
            rel32=struct.unpack("<i",code[i+1:i+5])[0]
            dest=BASE+i+5+rel32
            if dest==target:
                out.append(BASE+i)
        i=code.find(pat_prefix,i+1)
    return out

for t in (0x47fc60,0x47ff50):
    calls=find_calls(t)
    print(f"\n===== callers of 0x{t:06x}: {len(calls)} =====")
    funcs={}
    for c in calls:
        f=enclosing(c-BASE)
        funcs.setdefault(f,[]).append(c)
    for f in sorted(funcs):
        print(f"  func 0x{f:06x}: call sites {[hex(x) for x in funcs[f]]}")
