from capstone import Cs, CS_ARCH_X86, CS_MODE_32
mem=open(r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin","rb").read()
BASE=0x400000
def rd(va,n): return mem[va-BASE:va-BASE+n]
def disasm(va, length):
    md=Cs(CS_ARCH_X86, CS_MODE_32); md.detail=True
    for ins in md.disasm(mem[va-BASE: va-BASE+length], va):
        print(f"{ins.address:08x}  "+" ".join(f"{b:02x}" for b in ins.bytes).ljust(18)+f"{ins.mnemonic} {ins.op_str}")

# thunk table around 0x4fb000
for t in (0x4fb0a8, 0x4fb09c):
    ptr = struct.unpack("<I", rd(t,4))[0] if False else int.from_bytes(rd(t,4),"little")
    print(f"\n=== thunk @{t:#x} -> {ptr:#x} ===")
    # if target within image, disassemble
    if 0x400000 < ptr < 0x600000:
        disasm(ptr, 0x60)
    else:
        print("  (external/import)", hex(ptr))
