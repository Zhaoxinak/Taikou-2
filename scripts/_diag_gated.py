import sys, os, json
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT)
from emu_harness import Emu
from unicorn import *
from unicorn.x86_const import *
BASE=0x400000; SET_C=0x49c500; BUF=0x5203c0
ENT_BASE=0x519868; ENT_STRIDE=0x47B; SEGC=BUF+0x13

def make_emu():
    e=Emu()
    try: e.mu.mem_map(0x3000,0x1000); e.mu.mem_write(0x3000,b"\xc3"*0x1000)
    except Exception: pass
    return e

def run(owner, target_call, entity_idx=0, gates=None, steps=0x100000):
    e=make_emu()
    ent=ENT_BASE+entity_idx*ENT_STRIDE
    try:
        e.mu.mem_map(0,0x1000)
        d=bytes(e.mu.mem_read(ent,ENT_STRIDE))
        e.mu.mem_write(0, d+b"\x00"*(0x1000-ENT_STRIDE))
    except Exception: pass
    for a,v in (gates or {}).items(): e.mu.mem_write(a, bytes([v]))
    caps=[]; last=[0]; hit=[False]
    def hk(mu,ad,sz,ud):
        last[0]=ad
        if ad==0x4110e3: mu.reg_write(UC_X86_REG_EDI,ent)
        elif ad==0x4110e8: mu.reg_write(UC_X86_REG_ESI,ent)
        elif ad==0x413db7: mu.reg_write(UC_X86_REG_ESI,ent)
        elif ad==SET_C:
            esp=mu.reg_read(UC_X86_REG_ESP)
            ra=int.from_bytes(mu.mem_read(esp,4),'little')
            cs=ra-5
            idx=int.from_bytes(mu.mem_read(esp+4,4),'little')&0xff
            val=int.from_bytes(mu.mem_read(esp+8,1),'little')
            caps.append((cs,idx,val))
            if cs==target_call:
                hit[0]=True; mu.emu_stop()
    h=e.mu.hook_add(UC_HOOK_CODE,hk)
    err=None
    try: e.call(owner,[0,0,0,0,ent],regs={UC_X86_REG_ECX:BUF,UC_X86_REG_EBX:ent},max_steps=steps)
    except Exception as ex: err=str(ex)[:70]
    e.mu.hook_del(h)
    return caps,hit[0],err,last[0]

img=open(os.path.join(ROOT,"_unpacked_mem.bin"),"rb").read()
print("静态 segC[0..5] =", [img[SEGC-BASE+i] for i in range(6)])
print("静态 byte[0x513540] =", img[0x513540-BASE], " word[0x518588] =", int.from_bytes(img[0x518588-BASE:0x518588-BASE+2],'little'))
print()
CASES=[
 ("0x409300 owner=0x409250 gate=segC[0]=30", 0x409250, 0x409300, {SEGC+0:30}),
 ("0x409300 owner=0x409250 无门控",           0x409250, 0x409300, None),
 ("0x40c4f3 owner=0x40c4d0(修正)",            0x40c4d0, 0x40c4f3, None),
 ("0x40a6ec owner=0x40a620(修正)",            0x40a620, 0x40a6ec, None),
]
for name,ow,tc,g in CASES:
    caps,hit,err,last=run(ow,tc,0,g)
    print(f"--- {name}")
    print(f"    hit={hit} caps={[(hex(a),b,c) for a,b,c in caps]} err={err} last=0x{last:x}")
