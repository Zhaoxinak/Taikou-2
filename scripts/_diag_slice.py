import sys, os
ROOT=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,ROOT)
from emu_harness import Emu
from unicorn import *
from unicorn.x86_const import *
BUF=0x5203c0; SET_C=0x49c500; SEGC=BUF+0x13
def slice_run(entry,target,gates=None,steps=0x20000):
    e=Emu()
    try: e.mu.mem_map(0x3000,0x1000); e.mu.mem_write(0x3000,b"\xc3"*0x1000)
    except Exception: pass
    for a,v in (gates or {}).items(): e.mu.mem_write(a,bytes([v]))
    caps=[]
    def hk(mu,ad,sz,ud):
        if ad==SET_C:
            esp=mu.reg_read(UC_X86_REG_ESP)
            cs=int.from_bytes(mu.mem_read(esp,4),'little')-5
            idx=int.from_bytes(mu.mem_read(esp+4,4),'little')&0xff
            val=int.from_bytes(mu.mem_read(esp+8,1),'little')
            caps.append((cs,idx,val))
            if cs==target: mu.emu_stop()
    e.mu.hook_add(UC_HOOK_CODE,hk)
    err=None
    try: e.call(entry,[],regs={UC_X86_REG_ECX:BUF},max_steps=steps)
    except Exception as ex: err=str(ex)[:50]
    return caps,err

print("== 0x40a6ec 切片入口 0x40a6c9，扫 byte[0x513540] ==")
print(" v    captured(idx,val)   预测 v<2?(v>>1)+1:v>>1")
ok=0; tot=0
for v in [0,1,2,3,4,7,8,15,16,50,99,200,255]:
    caps,err=slice_run(0x40a6c9,0x40a6ec,{0x513540:v})
    pred=(v>>1)+1 if v<2 else (v>>1)
    got=[(hex(a),b,c) for a,b,c in caps if a==0x40a6ec]
    tot+=1
    m="OK" if got and got[0][2]==pred else "MISMATCH"
    if m=="OK": ok+=1
    print(f" {v:<4} {str(got):<24} pred={pred:<4} {m} err={err}")
print(f"公式吻合 {ok}/{tot}")

print("\n== 0x409300 切片入口 0x4092e1，扫 segC[0] ==")
ok2=0;tot2=0
for v in [0,1,2,5,29,30,31,100,255]:
    caps,err=slice_run(0x4092e1,0x409300,{SEGC+0:v})
    pred=0 if v<=1 else v-1
    got=[(hex(a),b,c) for a,b,c in caps if a==0x409300]
    tot2+=1
    m="OK" if got and got[0][2]==pred else "MISMATCH"
    if m=="OK": ok2+=1
    print(f" {v:<4} {str(got):<24} pred={pred:<4} {m} err={err}")
print(f"公式吻合 {ok2}/{tot2}")
