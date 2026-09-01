import sys,os
ROOT=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,ROOT)
from emu_harness import Emu
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX,UC_X86_REG_ESI,UC_X86_REG_EIP
BUF=0x5203c0; SET_C=0x49c500; TBL=0x518588
def run(entry,force_esi=None):
    e=Emu()
    try: e.mu.mem_map(0x3000,0x1000); e.mu.mem_write(0x3000,b"\xc3"*0x1000)
    except Exception: pass
    caps=[];last=[0]
    def hk(mu,ad,sz,ud):
        last[0]=ad
        if ad==0x4097c3 and force_esi is not None:
            mu.reg_write(UC_X86_REG_ESI,force_esi)
        elif ad==0x4097f2:                       # 调用跳过：净栈 0、不动 edi
            mu.reg_write(UC_X86_REG_EIP,0x40980c)
        elif ad==SET_C:
            esp=mu.reg_read(UC_X86_REG_ESP)
            caps.append((int.from_bytes(mu.mem_read(esp,4),'little')-5,
                         int.from_bytes(mu.mem_read(esp+4,4),'little')&0xff,
                         int.from_bytes(mu.mem_read(esp+8,1),'little')))
    e.mu.hook_add(UC_HOOK_CODE,hk)
    err=None
    try: e.call(entry,[0,0,0,0],regs={UC_X86_REG_ECX:BUF},max_steps=0x40000)
    except Exception as ex: err=str(ex)[:50]
    return caps,err,last[0]

print("== 0x409814：调用跳过 + esi 扫描，验 edi=(esi-0x518588)/139 ==")
ok=tot=0
for k in [0,1,2,3,5,10,19,20,42,99,150,199]:
    caps,err,last=run(0x4097bc,TBL+139*k)
    got=[c for c in caps if c[0]==0x409814]
    tot+=1
    m = got and got[0][1]==1 and got[0][2]==(k&0xff)
    ok+= bool(m)
    print(f"  k={k:<4} esi=0x518588+139*{k}  caps={[(hex(a),b,d) for a,b,d in caps]} 预测val={k&0xff} {'OK' if m else 'MISMATCH'} err={err}")
print(f"公式吻合 {ok}/{tot}")
print("\n== esi=0（走 0x4097d0 分支 edi=0x14）==")
caps,err,last=run(0x4097bc,0)
print(f"  caps={[(hex(a),b,d) for a,b,d in caps]} err={err}   预测 (1,20)")
