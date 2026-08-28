import sys, struct
from capstone import *
MEM=open(r"scripts/_unpacked_mem.bin","rb").read(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32)
start=int(sys.argv[1],16); n=int(sys.argv[2],16)
off=start-BASE
for ins in md.disasm(MEM[off:off+n], start):
    tgt=''
    if ins.mnemonic=='call' and ins.op_str.startswith('0x'): tgt='   ; call'
    print(f"0x{ins.address:06x}  {ins.bytes.hex():<20s} {ins.mnemonic:<8s} {ins.op_str}{tgt}")
