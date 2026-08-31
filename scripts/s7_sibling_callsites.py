#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""找 0x49bfba 簇内三个紧凑 setter (+0x08 @0x49bfba / +0x0a @0x49bfca / +0x0b @0x49bfda) 的
   E8 call-site，并回溯一处确认 ecx 是否 = S7 条目。共享库陷阱见 续155。
"""
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BASE=0x400000
BIN="F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
SETTERS={"+0x08@0x49bfba":0x49bfba,"+0x0a@0x49bfca":0x49bfca,"+0x0b@0x49bfda":0x49bfda}

def load():
    with open(BIN,"rb") as f: return f.read()

def find_e8_calls(b,target):
    res=[];p=0;n=len(b)
    while p<n-5:
        if b[p]==0xE8:
            rel=struct.unpack_from("<i",b,p+1)[0]
            if (p+BASE)+5+rel==target: res.append(p+BASE)
        p+=1
    return res

def disasm_back(b,va,nbytes=100):
    md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=False
    off=va-BASE;start=max(0,off-nbytes)
    return [(i.address,i.mnemonic,i.op_str) for i in md.disasm(b[start:off+6],start+BASE)]

def main():
    b=load()
    for name,addr in SETTERS.items():
        calls=find_e8_calls(b,addr)
        print(f"\n{name}: {len(calls)} call-sites {[hex(c) for c in calls]}")
        if calls:
            # 回溯首个 call-site 的 ecx 来源
            site=calls[0]
            for (a,m,o) in disasm_back(b,site):
                if "0x516a28" in o or (m=="lea" and "ecx" in o) or ("ecx" in o and "0x51" in o):
                    tag=" <== S7" if "0x516a28" in o else ""
                    print(f"   0x{a:x}: {m} {o}{tag}")

if __name__=="__main__":
    main()
