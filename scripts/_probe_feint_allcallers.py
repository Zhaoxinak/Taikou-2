#!/usr/bin/env python3
# 续233: classify all 29 callers of 0x43a440 by the argument they push.
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BASE=0x400000
MEM=open("/Users/ts/Downloads/Taikou 2/scripts/_unpacked_mem.bin","rb").read()
def read(va,n): return MEM[va-BASE:va-BASE+n]
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
CALLERS=[0x427779,0x428342,0x4284b8,0x428780,0x428b28,0x428c6a,0x428db3,
         0x42922d,0x429a28,0x429ba1,0x42c25c,0x42c2c3,0x43568c,0x436f0a,
         0x43a797,0x43a8cc,0x43a95d,0x43ab92,0x43ad11,0x43ae1a,0x43b1a5,
         0x43bb01,0x43bdfa,0x43c076,0x43c381,0x43c49e,0x43c655,0x43c74a,0x43d5a8]

PAT6=['movzx','cdq','xor','sub','and','lea','shl','push']  # signature of 6*x pattern
def classify(cva):
    code=read(cva-70, 80)
    insts=list(md.disasm(code, cva-70))
    # find idx of call
    callidx=None
    for i,ins in enumerate(insts):
        if ins.address==cva: callidx=i; break
    if callidx is None: return "no-call-in-window"
    # examine preceding instructions for push of imm / push reg / the 6-pattern
    pre=[(ins.mnemonic,ins.op_str) for ins in insts[max(0,callidx-12):callidx]]
    joined=' '.join('%s %s'%(m,o) for m,o in pre)
    is6 = ('shl' in joined and 'lea' in joined and 'cdq' in joined and 'movzx' in joined)
    # last push before call
    lastpush=None
    for m,o in pre:
        if m=='push': lastpush=o
    return is6, lastpush, pre[-4:]

for cva in CALLERS:
    is6,lp,tail=classify(cva)
    tag='[6*sign pattern]' if is6 else '[real-id?]'
    print("0x%06x %s  lastpush=%s  tail=%s"%(cva,tag,lp,[ (m,o) for m,o in tail]))
