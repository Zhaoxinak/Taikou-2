from capstone import Cs, CS_ARCH_X86, CS_MODE_32
MEM = open(r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin", "rb").read()
BASE = 0x400000
def off_of(va): return va - BASE
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

# disassemble 0x4e87e0 (status renderer) and find castle-lord flag computation
va = 0x4e87e0
code = MEM[off_of(va):off_of(va)+0x300]
lines = [f"{i.address:08x}  {i.mnemonic} {i.op_str}" for i in md.disasm(code, va)]
with open(r"F:/Games/Taikou 2/scripts/_renderer_flag.txt", "w", encoding="utf-8") as f:
    f.write("=== 0x4e87e0 status renderer (castle-lord flag hunt) ===\n")
    f.write("\n".join(lines))

# also scan: any 'and ..., 4' / 'test ..., 4' / reference to 0x516638 within
hits_flag = [l for l in lines if "516638" in l or ("4" in l and ("test" in l or "and" in l))]
print(f"[OK ] rendered {len(lines)} instrs; flag-related: {len(hits_flag)}")
for h in hits_flag[:40]:
    print("   ", h)
