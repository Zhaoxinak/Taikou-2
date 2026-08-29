from capstone import Cs, CS_ARCH_X86, CS_MODE_32
mem=open("_unpacked_mem.bin","rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
START,END=0x4e85e0,0x4e8b00
out=[]
for ins in md.disasm(mem[START-base:END-base],START):
    if ins.address>END: break
    out.append("%08x  %-9s %s"%(ins.address,ins.mnemonic,ins.op_str))
open("_sndata_mainloop.asm","w").write("\n".join(out))
# print lines around the two record-loop call sites
for target in ("call 0x47fc60","call 0x47fd10","call 0x47ff68","call 0x47ff50"):
    print("\n==== %s ===="%target)
    hits=[i for i,l in enumerate(out) if target in l]
    for h in hits:
        for l in out[max(0,h-12):h+3]:
            print("  "+l)
