from capstone import *

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
with open(MEM_PATH, "rb") as f:
    MEM = f.read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def dis(va, n=140):
    off = va - BASE
    out = []; cnt = 0
    for ins in md.disasm(MEM[off:off+0x800], va):
        out.append(f"{ins.address:#010x}: {ins.mnemonic} {ins.op_str}")
        cnt += 1
        if cnt >= n: break
    return "\n".join(out)

print(dis(0x468220, 200))
