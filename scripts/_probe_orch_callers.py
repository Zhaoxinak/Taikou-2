import struct
from capstone import *

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
with open(MEM_PATH, "rb") as f:
    MEM = f.read()
SIZE = len(MEM)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def e8_callers(*targets):
    tset=set(targets); res={t:[] for t in targets}; p=0
    while p < SIZE:
        if MEM[p]==0xe8 and p+5<=SIZE:
            r=struct.unpack("<i",MEM[p+1:p+5])[0]
            t=(p+BASE+5+r)&0xffffffff
            if t in tset: res[t].append(p+BASE)
            p+=5
        else: p+=1
    return res

print("e8 callers of 0x469840 (AI orchestrator) and 0x4696a0 (end):")
for t,cs in e8_callers(0x469840, 0x4696a0).items():
    print(f"  {t:#010x}: {[hex(c) for c in cs]}")

def dis(va,n=80):
    off=va-BASE; out=[];c=0
    for ins in md.disasm(MEM[off:off+0x400],va):
        out.append(f"{ins.address:#010x}: {ins.mnemonic} {ins.op_str}");c+=1
        if c>=n:break
    return "\n".join(out)

# Disassemble the callers to see if they pre-set this+0xc for AI
for c in e8_callers(0x469840, 0x4696a0)[0x469840]:
    print(f"\n--- caller of 0x469840 @ {c:#010x} ---")
    print(dis(c-0x40, 60))
