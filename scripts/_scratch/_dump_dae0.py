from capstone import Cs, CS_ARCH_X86, CS_MODE_32
mem=open("_unpacked_mem.bin","rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
def dump(start,size,label):
    print("==== %s @0x%x ===="%(label,start))
    n=0
    for ins in md.disasm(mem[start-base:start-base+size],start):
        print("%08x  %-9s %s"%(ins.address,ins.mnemonic,ins.op_str))
        n+=1
        if n>120: break
# dump a few sub-parsers
for f in (0x47dae0,0x47dce0,0x47e130):
    dump(f,0x280,"fn 0x%x"%f)
