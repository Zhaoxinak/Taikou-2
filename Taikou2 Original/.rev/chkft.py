import struct, capstone
f=open(r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_ft2.exe','rb').read()
DELTA=0xC00; base=0x400000
def off(rva): return rva-DELTA
def rva(va): return va-base
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
def dis(va,n=40):
    o=off(rva(va)); buf=f[o:o+n*8]
    for ins in md.disasm(buf,va):
        print("0x%06x: %-7s %s"%(ins.address,ins.mnemonic,ins.op_str))
        n-=1
        if n<=0: break
print("=== 调查卡挂钩 @0x46e31f (应 jmp nav_kbd) ===")
dis(0x46e31f,3)
print("=== nav_kbd @0x5352C0 ===")
dis(0x5352C0,14)
print("=== ft_kbd @0x535200 ===")
dis(0x535200,33)
