import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
mem=open(r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin","rb").read()
BASE=0x400000
def disasm(va, length, stop=None):
    md=Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail=True
    code=mem[va-BASE: va-BASE+length]
    out=[]
    for ins in md.disasm(code, va):
        s=f"{ins.address:08x}  " + " ".join(f"{b:02x}" for b in ins.bytes).ljust(20) + f"{ins.mnemonic} {ins.op_str}"
        out.append(s)
        if stop and ins.mnemonic=='ret':
            break
    return out

# check pixel data magic at entry0 + 0x310
f=open(r"F:/Games/Taikou2/NPKDATA.IDX","rb").read()
o=96
px=f[o+0x310:o+0x310+16]
print("entry0 pixel[0x310..]:", px.hex(), "ASCII:", px[:4])
px2=f[o+0x310-0x10:o+0x310+8]
print("around 0x300:", px2.hex())

print("\n===== 0x476390 (entry parser) =====")
for l in disasm(0x476390, 0x180): print(l)
