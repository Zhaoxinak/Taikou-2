import sys,os
ROOT=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,ROOT)
sys.argv=[sys.argv[0]]
import importlib.util
spec=importlib.util.spec_from_file_location("g",os.path.join(ROOT,"s15_segc_gated_capture_ref.py"))
# 不执行 ref（会 sys.exit），直接复制最小 harness
from emu_harness import Emu
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX,UC_X86_REG_EDI,UC_X86_REG_ESI
BUF=0x5203c0; SEGC=BUF+0x13; SET_C=0x49c500
ENT_BASE,ENT_STRIDE=0x519868,0x47B
def cap(entry,gates=None,steps=0x200000):
    e=Emu()
    try: e.mu.mem_map(0x3000,0x1000); e.mu.mem_write(0x3000,b"\xc3"*0x1000)
    except Exception: pass
    ent=ENT_BASE
    try:
        e.mu.mem_map(0,0x1000)
        e.mu.mem_write(0,bytes(e.mu.mem_read(ent,ENT_STRIDE))+b"\x00"*(0x1000-ENT_STRIDE))
    except Exception: pass
    for a,v in (gates or {}).items(): e.mu.mem_write(a,bytes([v&0xff]))
    caps=[];last=[0]
    def hk(mu,ad,sz,ud):
        last[0]=ad
        if ad==0x4110e3: mu.reg_write(UC_X86_REG_EDI,ent)
        elif ad==0x4110e8: mu.reg_write(UC_X86_REG_ESI,ent)
        elif ad==0x413db7: mu.reg_write(UC_X86_REG_ESI,ent)
        elif ad==SET_C:
            esp=mu.reg_read(UC_X86_REG_ESP)
            caps.append((int.from_bytes(mu.mem_read(esp,4),'little')-5,
                         int.from_bytes(mu.mem_read(esp+4,4),'little')&0xff,
                         int.from_bytes(mu.mem_read(esp+8,1),'little')))
    e.mu.hook_add(UC_HOOK_CODE,hk)
    err=None
    try: e.call(entry,[0,0,0,0],regs={UC_X86_REG_ECX:BUF},max_steps=steps)
    except Exception as ex: err=str(ex)[:55]
    return caps,err,last[0]

print("== 0x413d10  模式 si=(word[0x520604]>>12)&3 ==")
for name,g in [("si=0 零态",None),("si=3 byte[0x520605]=0x30",{0x520605:0x30}),
               ("si=2 byte[0x520605]=0x20",{0x520605:0x20}),("si=1 byte[0x520605]=0x10",{0x520605:0x10})]:
    c,err,last=cap(0x413d10,g)
    print(f"  {name:<28} caps={[(hex(a),b,d) for a,b,d in c]} err={err} last=0x{last:x}")

print("\n== 0x4097a0 全函数 ==")
c,err,last=cap(0x4097a0)
print(f"  caps={[(hex(a),b,d) for a,b,d in c]} err={err} last=0x{last:x}")
print("\n== 0x4097a0 切片起点 0x4097bc（跳过前置 imm 写） ==")
c,err,last=cap(0x4097bc)
print(f"  caps={[(hex(a),b,d) for a,b,d in c]} err={err} last=0x{last:x}")
print("\n== 0x409814 最小切片：0x40980c (edi 已定) ==")
c,err,last=cap(0x4097f2)
print(f"  from 0x4097f2 caps={[(hex(a),b,d) for a,b,d in c]} err={err} last=0x{last:x}")
