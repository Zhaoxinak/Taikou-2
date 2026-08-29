from capstone import Cs, CS_ARCH_X86, CS_MODE_32
mem=open(r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin","rb").read()
def disasm(va, length):
    md=Cs(CS_ARCH_X86, CS_MODE_32)
    for ins in md.disasm(mem[va-0x400000: va-0x400000+length], va):
        print(f"{ins.address:08x}  "+" ".join(f"{b:02x}" for b in ins.bytes).ljust(18)+f"{ins.mnemonic} {ins.op_str}")
print("=== 0x441170 (read bytes) ===")
disasm(0x441170, 0x60)
print("\n=== 0x4411f0 (init bit reader?) ===")
disasm(0x4411f0, 0x80)
print("\n=== 0x441210 (read source byte) ===")
disasm(0x441210, 0x50)
