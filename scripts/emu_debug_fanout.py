#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试：idx=100 调 0x47fc60 后，打印两个候选缓冲基址 + 3 个全局，定位记录真正落点。"""
import os
import struct
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); BIN=ROOT+"/scripts/_unpacked_mem.bin"; BASE=0x400000
class Emu:
    def __init__(s):
        s.mu=Uc(UC_ARCH_X86,UC_MODE_32); s.code=open(BIN,"rb").read()
        s.mu.mem_map(BASE,len(s.code)); s.mu.mem_write(BASE,s.code)
        s.STACK_TOP=0x600000; s.mu.mem_map(s.STACK_TOP,0x40000)
        s.STOP=0x700000; s.mu.mem_map(s.STOP,0x1000); s.mu.mem_write(s.STOP,b"\x90"*4)
        s.last=[0]; s.mu.hook_add(UC_HOOK_CODE,lambda mu,a,ss,u:s.last.__setitem__(0,a))
    def _st(s,mu,a,ss,u):
        if a==s.STOP: mu.emu_stop()
    def write(s,a,d): s.mu.mem_write(a,d)
    def read(s,a,n): return bytes(s.mu.mem_read(a,n))
    def alloc(s,size,at=None):
        if at is None: at=getattr(s,'_ap',0x800000); s._ap=at+((size+0xfff)&~0xfff)+0x1000
        at&=~0xfff; s.mu.mem_map(at,max((size+0xfff)&~0xfff,0x1000)); return at
    def call(s,va,args=(),arg_off=4):
        esp=s.STACK_TOP+0x40000-0x2000; s.write(esp,struct.pack("<I",s.STOP))
        for i,a in enumerate(args): s.write(esp+arg_off+i*4,struct.pack("<I",a&0xffffffff))
        s.mu.reg_write(UC_X86_REG_ESP,esp); s.mu.reg_write(UC_X86_REG_EIP,va)
        h=s.mu.hook_add(UC_HOOK_CODE,s._st)
        try: s.mu.emu_start(va,s.STOP+1,count=0x200000)
        finally: s.mu.hook_del(h)

def main():
    e=Emu(); SND=open(ROOT+"/Taikou2 Original/SNDATA1.TR2","rb").read()
    BUF=e.alloc(len(SND)); e.write(BUF,SND)
    STUB_LSEEK,STUB_READ,STUB_FLUSH=0x900000,0x900010,0x900020
    e.mu.mem_map(0x900000,0x1000); e.write(0x900000,b"\xc3"*0x1000)
    e.write(0x4fb0a8,struct.pack("<I",STUB_LSEEK)); e.write(0x4fb0a0,struct.pack("<I",STUB_READ)); e.write(0x4fb09c,struct.pack("<I",STUB_FLUSH))
    pos=[0]; copies=[]
    def on(mu,ad,size,ud):
        sp=mu.reg_read(UC_X86_REG_ESP)
        if ad==STUB_LSEEK:
            off=struct.unpack("<I",mu.mem_read(sp+8,4))[0]; pos[0]=off
            r=struct.unpack("<I",mu.mem_read(sp,4))[0]; mu.reg_write(UC_X86_REG_EAX,off); mu.reg_write(UC_X86_REG_ESP,sp+16); mu.reg_write(UC_X86_REG_EIP,r)
        elif ad==STUB_READ:
            dst=struct.unpack("<I",mu.mem_read(sp+8,4))[0]; cnt=struct.unpack("<I",mu.mem_read(sp+0xc,4))[0]
            n=min(cnt,len(SND)-pos[0]); mu.mem_write(dst,SND[pos[0]:pos[0]+n]); pos[0]+=n
            r=struct.unpack("<I",mu.mem_read(sp,4))[0]; mu.reg_write(UC_X86_REG_EAX,n); mu.reg_write(UC_X86_REG_ESP,sp+16); mu.reg_write(UC_X86_REG_EIP,r)
        elif ad==STUB_FLUSH:
            r=struct.unpack("<I",mu.mem_read(sp,4))[0]; mu.reg_write(UC_X86_REG_EAX,0); mu.reg_write(UC_X86_REG_ESP,sp+8); mu.reg_write(UC_X86_REG_EIP,r)
        elif ad==0x47d720:
            r=struct.unpack("<I",mu.mem_read(sp,4))[0]; mu.reg_write(UC_X86_REG_EAX,1); mu.reg_write(UC_X86_REG_ESP,sp+12); mu.reg_write(UC_X86_REG_EIP,r)
        elif ad==0x4ebfe0:
            d=struct.unpack("<I",mu.mem_read(sp+4,4))[0]; s=struct.unpack("<I",mu.mem_read(sp+8,4))[0]; copies.append((d,s))
    e.mu.hook_add(UC_HOOK_CODE,on)
    idx=100; IDW,SUBW,FL=e.alloc(8),e.alloc(8),e.alloc(8)
    e.write(0x522c88,b"\x00"*64); e.write(0x522c60,b"\x00"*48); e.write(0x522c70,b"\x00"*32)
    e.write(0x63d000,b"\x00"*0x1000); pos[0]=0; copies.clear()
    e.call(0x47fc60,args=[idx,IDW,SUBW,FL])
    rec=SND[16+idx*49:16+idx*49+49]
    for base in (0x63de2c,0x63df2c):
        b=e.read(base,49)
        print(f"buf@{base:#08x}: match_rec={b==rec}  hex={b.hex()}")
    print(f"rec        : {rec.hex()}")
    print("copies (dst,src):")
    for d,s in copies:
        off=s-0x63df2c
        print(f"  dst={d:#08x} src={s:#08x} src_off(buf+0x63df2c)={off:#x}")
    for g in (0x522c88,0x522c60,0x522c70):
        print(f"  global {g:#08x}: {e.read(g,43).hex()}")
    # 在 rec 中找各全局内容的起始偏移
    for g in (0x522c88,0x522c60,0x522c70):
        data=e.read(g,43)
        # 截到首个 null
        k=data.find(b"\x00"); data=data[:k] if k>=0 else data
        pos_in_rec=rec.find(data)
        print(f"  global {g:#08x} content(nt)={data.hex()}  found_in_rec@offset={pos_in_rec}")
main()
