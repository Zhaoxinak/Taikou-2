import struct, re
from capstone import *

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
with open(MEM_PATH, "rb") as f:
    MEM = f.read()
SIZE = len(MEM)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

# find prologue by scanning backward from 0x469840 for 'push ebp'/'push esi' style
def find_prologue(va, lookback=0x200):
    off = va - BASE
    # scan instructions backward is hard; instead scan bytes for 'push ebp' (55) followed by 'push esi'(56) / 'push edi'(57) / 'push ebx'(53)
    cand = []
    start = max(0, off-lookback)
    for i in range(start, off):
        if MEM[i]==0x55 and MEM[i+1] in (0x56,0x57,0x53,0x54):
            cand.append(i+BASE)
    return cand

pros = find_prologue(0x469840)
print("possible prologues before 0x469840:", [hex(p) for p in pros])

def dis(va, n=120):
    off=va-BASE; out=[];c=0
    for ins in md.disasm(MEM[off:off+0xA00],va):
        out.append(f"{ins.address:#010x}: {ins.mnemonic} {ins.op_str}");c+=1
        if c>=n:break
    return "\n".join(out)

# take the closest prologue at or before 0x469840
entry = max([p for p in pros if p <= 0x469840] or [0x469840])
print(f"\nassumed entry = {entry:#010x}\n")
print(dis(entry, 130))

# callers of this entry
def e8_callers(t):
    res=[];p=0
    while p<SIZE:
        if MEM[p]==0xe8 and p+5<=SIZE:
            r=struct.unpack("<i",MEM[p+1:p+5])[0]
            if (p+BASE+5+r)&0xffffffff==t: res.append(p+BASE)
            p+=5
        else:p+=1
    return res
print("\ncallers of entry:", [hex(c) for c in e8_callers(entry)])
