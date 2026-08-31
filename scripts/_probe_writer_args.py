from capstone import *

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
with open(MEM_PATH, "rb") as f:
    MEM = f.read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def dis(va, n=40):
    off = va - BASE
    out=[]; c=0
    for ins in md.disasm(MEM[off:off+0x200], va):
        out.append(f"{ins.address:#010x}: {ins.mnemonic} {ins.op_str}"); c+=1
        if c>=n: break
    return "\n".join(out)

print("="*72); print("Writer-caller args (0x4694e0 / 0x469530)"); print("="*72)
for va in (0x4484e0, 0x448a00, 0x447c10):
    print(f"\n--- around caller {va:#010x} ---")
    print(dis(va, 40))

print("\n" + "="*72); print("0x49f7a0 pre-ikill check (does it write this+0xc?)"); print("="*72)
print(dis(0x49f7a0, 50))
