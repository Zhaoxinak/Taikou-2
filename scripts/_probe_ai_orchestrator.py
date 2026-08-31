from capstone import *

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
with open(MEM_PATH, "rb") as f:
    MEM = f.read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def dis(va, n=120):
    off = va - BASE
    out=[]; c=0
    for ins in md.disasm(MEM[off:off+0x700], va):
        out.append(f"{ins.address:#010x}: {ins.mnemonic} {ins.op_str}"); c+=1
        if c>=n: break
    return "\n".join(out)

print("="*72); print("AI orchestrator region 0x469840..0x469900"); print("="*72)
print(dis(0x469840, 150))

print("\n" + "="*72); print("Writer-caller sites (arg setup)"); print("="*72)
for va in (0x446dba, 0x4918b8, 0x4d1bba, 0x448508, 0x448a2c, 0x447c37):
    print(f"\n--- caller {va:#010x} ---")
    print(dis(va-0x30, 30))
