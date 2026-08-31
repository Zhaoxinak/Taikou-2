import struct
from capstone import *

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
with open(MEM_PATH, "rb") as f:
    MEM = f.read()
SIZE = len(MEM)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def e8_callers(t):
    res=[];p=0
    while p<SIZE:
        if MEM[p]==0xe8 and p+5<=SIZE:
            r=struct.unpack("<i",MEM[p+1:p+5])[0]
            if (p+BASE+5+r)&0xffffffff==t: res.append(p+BASE)
            p+=5
        else:p+=1
    return res

def dis(va,n=80):
    off=va-BASE; out=[];c=0
    for ins in md.disasm(MEM[off:off+0x600],va):
        out.append(f"{ins.address:#010x}: {ins.mnemonic} {ins.op_str}");c+=1
        if c>=n:break
    return "\n".join(out)

print("callers of 0x468220 (special submenu):", [hex(c) for c in e8_callers(0x468220)])
for c in e8_callers(0x468220):
    print(f"\n--- dispatcher caller {c:#010x} ---")
    print(dis(c-0x30, 60))
