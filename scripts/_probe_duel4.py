# -*- coding: utf-8 -*-
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
MEM = open(r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin", "rb").read()
BASE=0x400000; cs=Cs(CS_ARCH_X86,CS_MODE_32); cs.detail=True
def dump(addr,bytes_,tag):
    print(f"\n==== {tag} @ {addr:#010x} ({bytes_}B) ====")
    off=addr-BASE
    for ins in cs.disasm(MEM[off:off+bytes_],addr):
        print(f"  {ins.address:#010x}  {ins.mnemonic} {ins.op_str}")

# 调度器：跳表 0x4684c0 的 disp32 = c0 84 44 00，找前后字节
print("==== scan disp32 0x4684c0 (c0 84 44 00) ====")
i=0
while i+4 < len(MEM):
    if MEM[i]==0xc0 and MEM[i+1]==0x84 and MEM[i+2]==0x44 and MEM[i+3]==0x00:
        ctx = MEM[i-3:i+5]
        print(f"  0x{BASE+i-3:08x}  bytes: {ctx.hex()}")
    i+=1

dump(0x4680e0, 160, "一击必杀 0x468000 tail")
dump(0x467a70, 210, "MOD 0x467a70 (击中要害收尾修正)")
dump(0x46b6e0, 120, "APPLY 0x46b6e0 (伤害应用?)")
