import sys, os
ROOT=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,ROOT)
from emu_harness import Emu
from unicorn import *
from unicorn.x86_const import *
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from _disasm_all import disasm_all
BASE=0x400000; BUF=0x5203c0
img=open(os.path.join(ROOT,"_unpacked_mem.bin"),"rb").read()
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=False
def dis1(va):
    for i in disasm_all(md,img[va-BASE:va-BASE+16],va): return (i.mnemonic,i.op_str)
    return ("?","")
e=Emu()
try: e.mu.mem_map(0x3000,0x1000); e.mu.mem_write(0x3000,b"\xc3"*0x1000)
except Exception: pass
ring=[]
def hk(mu,ad,sz,ud): ring.append(ad)
e.mu.hook_add(UC_HOOK_CODE,hk)
try: e.call(0x40a620,[0,0,0,0],regs={UC_X86_REG_ECX:BUF},max_steps=0x100000)
except Exception: pass
depth=0
for a in ring:
    m,o=dis1(a)
    if m=="call":
        print(f"{'  '*min(depth,10)}0x{a:06x} call {o}")
        depth+=1
    elif m.startswith("ret"):
        depth=max(0,depth-1)
