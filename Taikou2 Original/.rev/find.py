import capstone
d=open('clean_dump.bin','rb').read()
base=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
# scan whole code for instructions referencing 0x516624 / 0x516610
targets={0x516624:'idxSUBJ',0x516610:'cardSTRUCT'}
rva=0x1000
end=len(d)
hits=[]
for addr in range(0x401000,0x401000+ (end-0x1000), 1):
    pass
