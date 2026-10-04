import sys
from capstone import *
d=bytearray(open('clean_dump.bin','rb').read())
base=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32)
def disasm(va,n=None,lines=None):
    rva=va-base
    buf=bytes(d[rva:rva+(n or (len(d)-rva))])
    cnt=0
    for ins in md.disasm(buf,va):
        print("0x%06x: %-8s %s %s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
        cnt+=1
        if lines and cnt>=lines: break
start=int(sys.argv[1],16)
if len(sys.argv)>2 and sys.argv[2]=='j':
    # jump table dump
    for i in range(0,int(sys.argv[3])):
        v=int.from_bytes(d[start+i*4-base:start+i*4-base+4],'little')
        print("case%d -> 0x%x"%(i,v))
else:
    n=int(sys.argv[2]) if len(sys.argv)>2 else 64
    disasm(start,lines=n)
