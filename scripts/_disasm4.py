from capstone import Cs, CS_ARCH_X86, CS_MODE_32
mem=open(r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin","rb").read()
def disasm(va, length):
    md=Cs(CS_ARCH_X86, CS_MODE_32)
    for ins in md.disasm(mem[va-0x400000: va-0x400000+length], va):
        print(f"{ins.address:08x}  "+" ".join(f"{b:02x}" for b in ins.bytes).ljust(18)+f"{ins.mnemonic} {ins.op_str}")
print("=== 0x4b2157 (else branch) -> continue to 0x4b2300 ===")
disasm(0x4b2157, 0x1b0)
