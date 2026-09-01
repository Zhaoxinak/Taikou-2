import sys, os
ROOT=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,ROOT)
from emu_harness import Emu
from unicorn import *
from unicorn.x86_const import *
BASE=0x400000; SET_C=0x49c500; BUF=0x5203c0; SEGC=BUF+0x13
ENT_BASE=0x519868; ENT_STRIDE=0x47B
# 资源加载器 0x4ec8c0: mov eax,1; ret 8  （stdcall 2 参，短路成功）
STUBS={0x4ec8c0: b"\xb8\x01\x00\x00\x00\xc2\x08\x00"}
def run(owner,target,entity_idx=0,gates=None,steps=0x200000,stub=True):
    e=Emu()
    try: e.mu.mem_map(0x3000,0x1000); e.mu.mem_write(0x3000,b"\xc3"*0x1000)
    except Exception: pass
    ent=ENT_BASE+entity_idx*ENT_STRIDE
    try:
        e.mu.mem_map(0,0x1000)
        e.mu.mem_write(0,bytes(e.mu.mem_read(ent,ENT_STRIDE))+b"\x00"*(0x1000-ENT_STRIDE))
    except Exception: pass
    if stub:
        for a,b in STUBS.items(): e.mu.mem_write(a,b)
    for a,v in (gates or {}).items(): e.mu.mem_write(a,bytes([v]))
    caps=[]; last=[0]; hit=[False]
    def hk(mu,ad,sz,ud):
        last[0]=ad
        if ad==SET_C:
            esp=mu.reg_read(UC_X86_REG_ESP)
            cs=int.from_bytes(mu.mem_read(esp,4),'little')-5
            idx=int.from_bytes(mu.mem_read(esp+4,4),'little')&0xff
            val=int.from_bytes(mu.mem_read(esp+8,1),'little')
            caps.append((cs,idx,val))
            if cs==target: hit[0]=True; mu.emu_stop()
    e.mu.hook_add(UC_HOOK_CODE,hk)
    err=None
    try: e.call(owner,[0,0,0,0],regs={UC_X86_REG_ECX:BUF},max_steps=steps)
    except Exception as ex: err=str(ex)[:60]
    return caps,hit[0],err,last[0]

for name,ow,tc,g in [
  ("0x40a6ec owner=0x40a620 +资源桩", 0x40a620,0x40a6ec,None),
  ("0x40a6ec owner=0x40a620 +资源桩 +byte[0x513540]=8", 0x40a620,0x40a6ec,{0x513540:8}),
  ("0x40a6ec owner=0x40a620 +资源桩 +byte[0x513540]=1", 0x40a620,0x40a6ec,{0x513540:1}),
]:
    caps,hit,err,last=run(ow,tc,0,g)
    print(f"--- {name}\n    hit={hit} caps={[(hex(a),b,c) for a,b,c in caps]} err={err} last=0x{last:x}")
