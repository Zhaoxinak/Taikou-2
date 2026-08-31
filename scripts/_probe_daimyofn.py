# -*- coding: utf-8 -*-
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
MEM = open(r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin", "rb").read()
BASE=0x400000; cs=Cs(CS_ARCH_X86,CS_MODE_32); cs.detail=True
def dump(addr,bytes_,tag):
    print(f"\n==== {tag} @ {addr:#010x} ({bytes_}B) ====")
    off=addr-BASE
    for ins in cs.disasm(MEM[off:off+bytes_],addr):
        print(f"  {ins.address:#010x}  {ins.mnemonic} {ins.op_str}")
dump(0x4c2b80, 640, "TERRITORY->DAIMYO fn (0x4c2c32= mov eax,0x5179b8)")
dump(0x4a3f80, 440, "SUCCESSION fn (0x4a4030 mid)")
