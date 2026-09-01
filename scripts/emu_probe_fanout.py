#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""探针：确定 0x47fc60 在 emu 下的参数落点（prologue sub esp,0xd4 后读 [esp+0xd8]）。
   用哨兵值调用，hook 0x47fc7b / 0x47d890 入口，打印实际读到的 idx。"""
import os
import struct
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN  = ROOT + "/scripts/_unpacked_mem.bin"
BASE = 0x400000

class Emu:
    def __init__(self, stack_top=0x600000, stack_size=0x40000, stop_page=0x700000):
        self.mu = Uc(UC_ARCH_X86, UC_MODE_32)
        with open(BIN, "rb") as f: self.code = f.read()
        self.mu.mem_map(BASE, len(self.code)); self.mu.mem_write(BASE, self.code)
        self.STACK_TOP = stack_top; self.mu.mem_map(stack_top, stack_size)
        self.STOP = stop_page; self.mu.mem_map(stop_page, 0x1000); self.mu.mem_write(stop_page, b"\x90"*4)
        self.last=[0]
        self.mu.hook_add(UC_HOOK_CODE, lambda mu,a,s,u: self.last.__setitem__(0,a))
    def _stop(self,mu,a,s,u):
        if a==self.STOP: mu.emu_stop()
    def write(self,a,d): self.mu.mem_write(a,d)
    def read(self,a,n): return bytes(self.mu.mem_read(a,n))
    def alloc(self,size,at=None):
        if at is None: at=getattr(self,'_ap',0x800000); self._ap=at+((size+0xfff)&~0xfff)+0x1000
        at&=~0xfff; self.mu.mem_map(at,max((size+0xfff)&~0xfff,0x1000)); return at
    def call(self,va,args=(),regs=None,arg_off=4,max_steps=0x200000):
        regs=regs or {}
        esp=self.STACK_TOP+0x40000-0x2000
        # 哨兵 retaddr
        self.write(esp, struct.pack("<I", self.STOP))
        # 同时把哨兵也写到可能的“下方”槽，便于观察
        for off in (0x4, 0xd4, 0xd8, 0xdc, 0xe0, 0xe4):
            self.write(esp+off, struct.pack("<I", self.STOP))
        for i,a in enumerate(args):
            self.write(esp+arg_off+i*4, struct.pack("<I", a & 0xffffffff))
        self.mu.reg_write(UC_X86_REG_ESP, esp)
        self.mu.reg_write(UC_X86_REG_EIP, va)
        for r,v in regs.items(): self.mu.reg_write(r,v&0xffffffff)
        h=self.mu.hook_add(UC_HOOK_CODE,self._stop)
        try: self.mu.emu_start(va,self.STOP+1,count=max_steps)
        except Exception as e:
            print(f"CRASH last_eip=0x{self.last[0]:06x}: {e}"); raise
        finally: self.mu.hook_del(h)

def main():
    e=Emu()
    SND=open(ROOT+"/Taikou2 Original/SNDATA1.TR2","rb").read()
    BUF=e.alloc(len(SND)); e.write(BUF,SND)
    STUB_LSEEK=0x900000; STUB_READ=0x900010; STUB_FLUSH=0x900020
    e.mu.mem_map(0x900000,0x1000); e.write(0x900000,b"\xc3"*0x1000)
    e.write(0x4fb0a8,struct.pack("<I",STUB_LSEEK))
    e.write(0x4fb0a0,struct.pack("<I",STUB_READ))
    e.write(0x4fb09c,struct.pack("<I",STUB_FLUSH))
    pos=[0]
    def on_code(mu,address,size,ud):
        sp=mu.reg_read(UC_X86_REG_ESP)
        if address==0x47fc7b:
            # mov ecx,[esp+0xd8]
            v=struct.unpack("<I",mu.mem_read(sp+0xd8,4))[0]
            print(f"  0x47fc7b: esp=0x{sp:06x}, [esp+0xd8]=0x{v:08x}  (期望 idx 哨兵)")
        elif address==0x47d890:
            idx=struct.unpack("<I",mu.mem_read(sp+4,4))[0]
            buf=struct.unpack("<I",mu.mem_read(sp+8,4))[0]
            print(f"  0x47d890 entry: esp=0x{sp:06x}, idx(arg@+4)=0x{idx:08x}, buffer(arg@+8)=0x{buf:08x}")
        elif address==STUB_LSEEK:
            off=struct.unpack("<I",mu.mem_read(sp+8,4))[0]; pos[0]=off
            ret=struct.unpack("<I",mu.mem_read(sp,4))[0]
            mu.reg_write(UC_X86_REG_EAX,off); mu.reg_write(UC_X86_REG_ESP,sp+16); mu.reg_write(UC_X86_REG_EIP,ret)
        elif address==STUB_READ:
            dst=struct.unpack("<I",mu.mem_read(sp+8,4))[0]; cnt=struct.unpack("<I",mu.mem_read(sp+0xc,4))[0]
            n=min(cnt,len(SND)-pos[0])
            if n<0:n=0
            mu.mem_write(dst,SND[pos[0]:pos[0]+n]); pos[0]+=n
            ret=struct.unpack("<I",mu.mem_read(sp,4))[0]
            mu.reg_write(UC_X86_REG_EAX,n); mu.reg_write(UC_X86_REG_ESP,sp+16); mu.reg_write(UC_X86_REG_EIP,ret)
        elif address==STUB_FLUSH:
            ret=struct.unpack("<I",mu.mem_read(sp,4))[0]
            mu.reg_write(UC_X86_REG_EAX,0); mu.reg_write(UC_X86_REG_ESP,sp+8); mu.reg_write(UC_X86_REG_EIP,ret)
        elif address==0x47d720:
            ret=struct.unpack("<I",mu.mem_read(sp,4))[0]
            mu.reg_write(UC_X86_REG_EAX,1); mu.reg_write(UC_X86_REG_ESP,sp+12); mu.reg_write(UC_X86_REG_EIP,ret)
    e.mu.hook_add(UC_HOOK_CODE,on_code)
    # 哨兵 idx = 0x1234，分配输出缓冲
    IDW=e.alloc(8); SUBW=e.alloc(8); FL=e.alloc(8)
    print("--- 调用 0x47fc60(idx=0x1234) 探测参数落点 ---")
    e.call(0x47fc60, args=[0x1234, IDW, SUBW, FL], arg_off=4)
    print(f"  IDW={e.read(IDW,2).hex()} SUBW={e.read(SUBW,2).hex()} FL={e.read(FL,2).hex()}")
    print(f"  0x522c88={e.read(0x522c88,16).hex()}")
    print(f"  local buf region (esp-0xd4..) : 见上方 idx 哨兵确认")

if __name__=="__main__":
    main()
