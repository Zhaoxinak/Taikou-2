from capstone import Cs, CS_ARCH_X86, CS_MODE_32
mem=open("_unpacked_mem.bin","rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
START,END=0x47d960,0x47f200
lines=[]
for ins in md.disasm(mem[START-base:END-base],START):
    if ins.address>END: break
    lines.append("%08x  %-9s %s"%(ins.address,ins.mnemonic,ins.op_str))
open("_sndata_parsers.asm","w").write("\n".join(lines))

# print context around every call 0x4411b0 / 0x4411d0 / 0x47d860 / 0x47d890
import re
idxs=[i for i,l in enumerate(lines) if ('call 0x4411b0' in l or 'call 0x4411d0' in l or 'call 0x47d860' in l or 'call 0x47d890' in l)]
print("total matched calls:", len(idxs))
for i in idxs:
    lo=max(0,i-4); hi=min(len(lines),i+2)
    blk=[lines[j] for j in range(lo,hi)]
    print("---- @%s ----"%lines[i].split()[0])
    for l in blk: print("   "+l)
