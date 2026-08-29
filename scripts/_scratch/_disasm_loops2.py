from capstone import Cs, CS_ARCH_X86, CS_MODE_32
mem=open("_unpacked_mem.bin","rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
def dump(s,e,label):
    print("\n==== %s 0x%x-0x%x ===="%(label,s,e))
    for ins in md.disasm(mem[s-base:e-base],s):
        if ins.address>e: break
        print("%08x  %-9s %s"%(ins.address,ins.mnemonic,ins.op_str))
# first loop around 0x4e8625 (call 0x47fc60)
dump(0x4e8625,0x4e8720,"LOOP1 @0x4e8625")
# second around 0x4e89cd (call 0x47fd10)
dump(0x4e89cd,0x4e8ad0,"LOOP2 @0x4e89cd")
