#!/usr/bin/env python3
# 找物品定义表索引器：搜索 ×19(0x13) 乘法 (imul reg,reg,0x13)，反汇编其前后来判断是否在索引 189×19 表。
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BIN = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
data = open(BIN,"rb").read()
def off(va): return va-BASE
cs = Cs(CS_ARCH_X86, CS_MODE_32); cs.detail=True

pats = [b"\x6b\xc0\x13", b"\x69\xc0\x13\x00\x00\x00",
        b"\x6b\xc9\x13", b"\x69\xc9\x13\x00\x00\x00",
        b"\x6b\xd2\x13", b"\x69\xd2\x13\x00\x00\x00",
        b"\x6b\xf3\x13", b"\x69\xf3\x13\x00\x00\x00",
        b"\x6b\xfa\x13", b"\x69\xfa\x13\x00\x00\x00"]
hits=[]
for p in pats:
    start=0
    while True:
        i=data.find(p,start)
        if i<0: break
        hits.append(i); start=i+1
print(f"x19 (imul 0x13) hits: {len(hits)}")
for i in hits[:40]:
    va=BASE+i
    code=data[i-0x50:i+0x10]
    print(f"\n----- x19 @ {va:#08x} -----")
    for ins in cs.disasm(code, va-0x50):
        print(f"{ins.address:#08x}  {ins.mnemonic} {ins.op_str}")
