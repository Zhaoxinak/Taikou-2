from capstone import *

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
with open(MEM_PATH, "rb") as f:
    MEM = f.read()
SIZE = len(MEM)

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def dis(va, n=60):
    off = va - BASE
    out = []
    cnt = 0
    for ins in md.disasm(MEM[off:off+0x600], va):
        out.append(f"{ins.address:#010x}: {ins.mnemonic} {ins.op_str}")
        cnt += 1
        if cnt >= n:
            break
    return "\n".join(out)

def dis_range(va_start, va_end):
    off = va_start - BASE
    endoff = va_end - BASE
    out = []
    for ins in md.disasm(MEM[off:endoff], va_start):
        out.append(f"{ins.address:#010x}: {ins.mnemonic} {ins.op_str}")
    return "\n".join(out)

print("="*72)
print("SPECIAL submenu callback 0x468250 (entry)")
print("="*72)
print(dis(0x468250, 50))

print("\n" + "="*72)
print("PLAYER main menu callback 0x469180")
print("="*72)
print(dis(0x469180, 50))

print("\n" + "="*72)
print("WRITER 0x469480 full")
print("="*72)
print(dis(0x469480, 40))

print("\n" + "="*72)
print("WRITER 0x4694aa full")
print("="*72)
print(dis(0x4694aa, 40))

print("\n" + "="*72)
print("WRITER 0x46950c full")
print("="*72)
print(dis(0x46950c, 40))

print("\n" + "="*72)
print("WRITER 0x469547 full")
print("="*72)
print(dis(0x469547, 40))
