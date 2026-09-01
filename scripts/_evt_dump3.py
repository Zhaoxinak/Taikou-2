# -*- coding: utf-8 -*-

# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>
import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *
BASE=0x400000
MEM=open(_ROOT + '/scripts/_unpacked_mem.bin','rb').read()
CODE_LO,CODE_HI=0x400000,0x600000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
def off(va): return va-BASE
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
if __name__=='__main__':
    for a in sys.argv[1:]:
        t=int(a,16)
        nxt=fn_next[t]
        if nxt-t>0x800: nxt=t+0x800
        insns=disasm_fn(t,nxt-t)
        print(f'--- 0x{t:x}  window={nxt-t:#x}  ninsns={len(insns)} ---')
        for i in insns[:30]:
            print(f'   0x{i.address:x}: {i.mnemonic} {i.op_str}')
        print()
