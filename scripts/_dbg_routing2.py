#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_dbg_routing2.py -- 调试 0x4e8625 循环：游标起点 + 0x4ec8c0 name 原始字节。"""
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p,'scripts')) and _os.path.isfile(_os.path.join(_p,'project.godot')):
            return _p
        _p=_os.path.dirname(_p)
    return _p
_ROOT=_find_root(_os.path.dirname(_os.path.abspath(__file__)))
import os, struct
from unicorn import UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX
from emu_sndata_read import Emu
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SND_PATH = os.path.join(ROOT, _ROOT + '/Taikou2 Original/SNDATA1.TR2')
CURSOR = 0x509684

def setup_stubs(e, SND):
    BUF = e.alloc(len(SND)); e.write(BUF, SND)
    STUB = 0x900000
    e.mem_map(STUB, 0x2000); e.write(STUB, b"\xc3"*0x2000)
    e.write(0x4fb0a8, struct.pack("<I", STUB+0x00))
    e.write(0x4fb0a0, struct.pack("<I", STUB+0x10))
    e.write(0x4fb09c, struct.pack("<I", STUB+0x20))
    e.write(0x4ebfe0, struct.pack("<I", STUB+0x30))
    e.write(0x4ebfc0, struct.pack("<I", STUB+0x40))
    e.write(0x4fb07c, struct.pack("<I", STUB+0x50))
    pos=[0]
    def on_code(mu, address, size, ud):
        sp = mu.reg_read(UC_X86_REG_ESP)
        if address==STUB+0x00:
            off=struct.unpack("<I",mu.mem_read(sp+8,4))[0]; pos[0]=off
            ret=struct.unpack("<I",mu.mem_read(sp,4))[0]
            mu.reg_write(UC_X86_REG_EAX, off&0xffffffff); mu.reg_write(UC_X86_REG_ESP, sp+16); mu.reg_write(UC_X86_REG_EIP, ret)
        elif address==STUB+0x10:
            dst=struct.unpack("<I",mu.mem_read(sp+8,4))[0]; cnt=struct.unpack("<I",mu.mem_read(sp+0xc,4))[0]
            n=min(cnt, len(SND)-pos[0])
            if n<0: n=0
            mu.mem_write(dst, SND[pos[0]:pos[0]+n]); pos[0]+=n
            ret=struct.unpack("<I",mu.mem_read(sp,4))[0]
            mu.reg_write(UC_X86_REG_EAX, n&0xffffffff); mu.reg_write(UC_X86_REG_ESP, sp+16); mu.reg_write(UC_X86_REG_EIP, ret)
        elif address==STUB+0x20:
            ret=struct.unpack("<I",mu.mem_read(sp,4))[0]; mu.reg_write(UC_X86_REG_EAX,0); mu.reg_write(UC_X86_REG_ESP, sp+8); mu.reg_write(UC_X86_REG_EIP, ret)
        elif address==STUB+0x30:
            ret=struct.unpack("<I",mu.mem_read(sp,4))[0]; mu.reg_write(UC_X86_REG_EIP, ret)
        elif address==STUB+0x40:
            ret=struct.unpack("<I",mu.mem_read(sp,4))[0]; mu.reg_write(UC_X86_REG_EAX,0); mu.reg_write(UC_X86_REG_EIP, ret)
        elif address==STUB+0x50:
            ret=struct.unpack("<I",mu.mem_read(sp,4))[0]; mu.reg_write(UC_X86_REG_EAX,1); mu.reg_write(UC_X86_REG_ESP, sp+16); mu.reg_write(UC_X86_REG_EIP, ret)
        elif address in (0x47d720,):
            ret=struct.unpack("<I",mu.mem_read(sp,4))[0]; mu.reg_write(UC_X86_REG_EAX,1); mu.reg_write(UC_X86_REG_ESP, sp+12); mu.reg_write(UC_X86_REG_EIP, ret)
        elif address in (0x47bde0,0x47ae80,0x47c080,0x47ae20,0x47b2e0,0x47d850):
            ret=struct.unpack("<I",mu.mem_read(sp,4))[0]; mu.reg_write(UC_X86_REG_EIP, ret)
    e.mu.hook_add(UC_HOOK_CODE, on_code)
    return BUF

def main():
    SND = open(SND_PATH,'rb').read()
    e = Emu()
    setup_stubs(e, SND)
    read_count=[0]; ec8c=[0]
    def on_code(mu, address, size, ud):
        if address==0x47d890:
            read_count[0]+=1
            idx=struct.unpack("<I",mu.mem_read(mu.reg_read(UC_X86_REG_ESP)+8,4))[0] if False else None
        elif address==0x4ec8c0:
            ec8c[0]+=1
            sp=mu.reg_read(UC_X86_REG_ESP)
            np_=struct.unpack("<I",mu.mem_read(sp+4,4))[0]
            try: raw=mu.mem_read(np_,16)
            except Exception: raw=b''
            s0=bytes(raw).split(b'\x00')[0]
            print("  0x4ec8c0 #%d: name_ptr=0x%06x bytes=%s str=%r" % (ec8c[0], np_, bytes(raw).hex(), s0))
    e.mu.hook_add(UC_HOOK_CODE, on_code)
    print("boot 0x47f350 ...")
    try: e.call(0x47f350, args=(), regs={}, max_steps=0x8000000); print("  OK")
    except Exception as ex: print(f"  CRASH @0x{e.last[0]:06x}: {ex}")

    # 试不同游标起点
    for start in (832, 833, 0):
        read_count[0]=0; ec8c[0]=0
        e.write(0x5205fe, struct.pack("<B", 0))
        e.write(CURSOR, struct.pack("<H", start))
        print(f"\n--- mode=0, cursor start={start} ---")
        try:
            e.call(0x4e8625, args=(), regs={}, max_steps=0x4000000)
            print(f"  完成: read_record×{read_count[0]}, 0x4ec8c0×{ec8c[0]}")
        except Exception as ex:
            print(f"  CRASH @0x{e.last[0]:06x}: {ex}; read_record×{read_count[0]}, 0x4ec8c0×{ec8c[0]}")
        cur=struct.unpack("<H",e.read(CURSOR,2))[0]
        print(f"  cursor 结束时=0x{cur:04x} ({cur})")
if __name__=='__main__':
    main()
