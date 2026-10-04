import sys, capstone
d=open('clean_dump.bin','rb').read()
base=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
want='0x%x'%int(sys.argv[1],16)
start=0x1000; endr=0x133000
for ins in md.disasm(d[start:endr], base+start):
    if want in ins.op_str:
        print("0x%06x: %-7s %s"%(ins.address,ins.mnemonic,ins.op_str))
