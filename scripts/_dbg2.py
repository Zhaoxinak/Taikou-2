# -*- coding: utf-8 -*-
import struct
from capstone import *
from capstone.x86 import *
BASE=0x400000
MEM=open('scripts/_unpacked_mem.bin','rb').read()
CODE_LO,CODE_HI=0x400000,0x600000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
def off(va): return va-BASE
CALL_CTX=0x49f6b0; CALL_FIRE=0x49b860
COND_JMP={'je','jne','jz','jnz','jg','jge','jae','jl','jle','jb','jbe','js','jns','jo','jno','jp','jnp','jc','jnc','loop','loope','loopne'}
FAM={}
for lo,hi in (('ax','eax'),('bx','ebx'),('cx','ecx'),('dx','edx'),('si','esi'),('di','edi'),('bp','ebp'),('sp','esp')):
    FAM[lo]={lo,hi}; FAM[hi]={lo,hi}
def same_fam(a,b): return a in FAM.get(b,set()) or b in FAM.get(a,set()) or a==b
fn_starts=set()
i=0;n=len(MEM)-5
while i<n:
    b=MEM[i]
    if b==0xE8:
        rel=struct.unpack('<i',MEM[i+1:i+5])[0]; tgt=(BASE+i+5+rel)&0xffffffff
        if CODE_LO<=tgt<CODE_HI: fn_starts.add(tgt)
    elif b in (0xC3,0xC2): fn_starts.add(BASE+i+1)
    elif b==0xE9:
        rel=struct.unpack('<i',MEM[i+1:i+5])[0]; tgt=(BASE+i+5+rel)&0xffffffff
        if tgt>BASE+i and CODE_LO<=tgt<CODE_HI: fn_starts.add(tgt)
    i+=1
k=0
while True:
    p=MEM.find(b'\x55\x89\xe5',k)
    if p<0: break
    fn_starts.add(BASE+p); k=p+1
fn_list=sorted(fn_starts)
fn_next={}
for kk in range(len(fn_list)):
    fn_next[fn_list[kk]]=fn_list[kk+1] if kk+1<len(fn_list) else fn_list[kk]+0x800
def disasm_fn(va,max_bytes):
    end=va+max_bytes; cur=va; out=[]
    while cur<end:
        chunk=MEM[off(cur):off(end)]; got=list(md.disasm(chunk,cur))
        if not got: cur+=1; continue
        for ins in got:
            if ins.address>=end: break
            out.append(ins)
        last=out[-1]; nxt=last.address+last.size; cur=nxt if nxt>cur else cur+1
    return out
fn=0x4499f0
nxt=fn_next[fn]
if nxt-fn>0x800: nxt=fn+0x800
insns=disasm_fn(fn,nxt-fn)
print(f"fn 0x{fn:x} nxt 0x{nxt:x} ninsns {len(insns)}")
ctx=fire=False
for ins in insns:
    if ins.mnemonic=='call' and ins.operands and ins.operands[0].type==CS_OP_IMM:
        t=ins.operands[0].imm&0xffffffff
        if t==CALL_CTX: ctx=True
        elif t==CALL_FIRE: fire=True
print(f"ctx={ctx} fire={fire}")
# find id loads
loads=[]
for idx,ins in enumerate(insns):
    if ins.mnemonic in ('mov','movzx','movsx') and len(ins.operands)==2:
        o0,o1=ins.operands[0],ins.operands[1]
        if o0.type==CS_OP_REG and o1.type==CS_OP_MEM and o1.mem.index==0 and o1.mem.disp==0:
            b=md.reg_name(o1.mem.base) if o1.mem.base else None
            if b: loads.append((idx,md.reg_name(o0.reg),b))
print("loads:",[(f'0x{idx:x}',r,b) for idx,r,b in loads])
# check cmp ax,0x1d region
for idx,ins in enumerate(insns):
    if ins.mnemonic=='cmp' and len(ins.operands)==2:
        o0,o1=ins.operands[0],ins.operands[1]
        if o1.type==CS_OP_IMM and (o1.imm&0xffff)==0x1d:
            print(f"  FOUND cmp imm 0x1d at 0x{ins.address:x}: {ins.mnemonic} {ins.op_str}")
            for kk in range(idx+1,min(idx+6,len(insns))):
                print(f"     next[{kk-idx}] 0x{insns[kk].address:x}: {insns[kk].mnemonic} {insns[kk].op_str}")
