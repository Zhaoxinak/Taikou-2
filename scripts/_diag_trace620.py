import sys, os
ROOT=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,ROOT)
from emu_harness import Emu
from unicorn import *
from unicorn.x86_const import *
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from _disasm_all import disasm_all
BASE=0x400000; SET_C=0x49c500; BUF=0x5203c0
img=open(os.path.join(ROOT,"_unpacked_mem.bin"),"rb").read()
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=False
def dis1(va):
    for i in disasm_all(md, img[va-BASE:va-BASE+16], va): return f"{i.mnemonic} {i.op_str}"
    return "?"
e=Emu()
try: e.mu.mem_map(0x3000,0x1000); e.mu.mem_write(0x3000,b"\xc3"*0x1000)
except Exception: pass
ring=[]
def hk(mu,ad,sz,ud):
    ring.append(ad)
    if len(ring)>4000: del ring[:2000]
h=e.mu.hook_add(UC_HOOK_CODE,hk)
err=None
try: e.call(0x40a620,[0,0,0,0],regs={UC_X86_REG_ECX:BUF},max_steps=0x100000)
except Exception as ex: err=str(ex)[:80]
print("err=",err,"steps~",len(ring))
# 找到首次跑出 0x400000..0x500000 代码区的跳转点
prev=None
for i,a in enumerate(ring):
    if a>=0x500000:
        prev=i; break
print("首次 PC>=0x500000 在第",prev,"步")
lo=max(0,(prev or len(ring))-14)
for a in ring[lo:(prev or len(ring))+3]:
    print(f"  0x{a:06x}  {dis1(a)}")
