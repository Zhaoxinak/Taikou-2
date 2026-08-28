from capstone import Cs, CS_ARCH_X86, CS_MODE_32
mem=open(r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin","rb").read()
def disasm(va, length, max_lines=200):
    md=Cs(CS_ARCH_X86, CS_MODE_32)
    n=0
    for ins in md.disasm(mem[va-0x400000: va-0x400000+length], va):
        print(f"{ins.address:08x}  "+" ".join(f"{b:02x}" for b in ins.bytes).ljust(18)+f"{ins.mnemonic} {ins.op_str}")
        n+=1
        if n>=max_lines: break
print("=== 0x4edb10 (wrapper called from parser 0x4b1fb0) ===")
disasm(0x4edb10, 0x400, max_lines=220)
