import os, struct, pickle, re
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

READERS=[0x47d3b0,0x47d580,0x47d680,0x47d6a0,0x47d720,0x47d780,0x47d800,0x47d850,0x47d860,0x47d890]

# Scan whole image for 'call <reader>' (E8 rel32) to each reader
def find_callers(tgt):
    callers=set()
    off=0
    while True:
        idx=code.find(b'\xe8', off)
        if idx<0: break
        rel=struct.unpack("<i", code[idx+1:idx+5])[0]
        va=BASE+idx+5+rel
        if va==tgt:
            callers.add(BASE+idx)
        off=idx+1
    return callers

buckets={}
for r in READERS:
    cs=find_callers(r)
    for site in cs:
        fn=enclosing(site)
        buckets.setdefault(fn, {}).setdefault(r, []).append(site)

print("caller fn (enclosing) | which 49B-readers used | #sites")
for fn in sorted(buckets):
    rs=list(buckets[fn].keys())
    tot=sum(len(v) for v in buckets[fn].values())
    print(f"  0x{fn+BASE:06x} | readers={[hex(r) for r in rs]} | sites={tot}")
print("\n(Done)")
