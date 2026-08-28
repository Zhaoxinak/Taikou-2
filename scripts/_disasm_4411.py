from capstone import Cs, CS_ARCH_X86, CS_MODE_32
mem=open(r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin","rb").read()
BASE=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32); md.detail=True
for va,length in [(0x4411b0,0x500),(0x441330,0x200),(0x441360,0x300)]:
    with open(f"F:/Games/Taikou 2/scripts/_disasm_{va:08x}.txt","w") as f:
        for ins in md.disasm(mem[va-BASE:va-BASE+length], va):
            f.write(f"{ins.address:08x}  "+" ".join(f"{b:02x}" for b in ins.bytes).ljust(20)+f"{ins.mnemonic} {ins.op_str}\n")
        print("wrote", hex(va))
