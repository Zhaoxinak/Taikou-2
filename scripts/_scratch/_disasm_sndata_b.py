from capstone import Cs, CS_ARCH_X86, CS_MODE_32
mem=open("_unpacked_mem.bin","rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
def disasm(s,e,label,out):
    out.append("==== %s (0x%x-0x%x) ===="%(label,s,e))
    for ins in md.disasm(mem[s-base:e-base],s):
        if ins.address>e: break
        out.append("%08x  %-9s %s"%(ins.address,ins.mnemonic,ins.op_str))
out=[]
disasm(0x47f340,0x47f740,"scene-block decoder 0x47f350 / reader 0x47f5c0",out)
disasm(0x47ff50,0x480100,"main record loop 0x47ff68",out)
open("_sndata_b.asm","w").write("\n".join(out))
print("ok lines",len(out))
