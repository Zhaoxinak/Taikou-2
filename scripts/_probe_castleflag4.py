from capstone import Cs, CS_ARCH_X86, CS_MODE_32
MEM = open(r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin", "rb").read()
BASE = 0x400000
def off_of(va): return va - BASE
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

# find 'mov <reg>, 0x516638' (b8+rd with imm=0x516638) or 'lea' etc.
target = 0x516638
writes = []
# registers: eax=0,bx? use b8..bf
for reg in range(8):
    pat = bytes([0xb8+reg]) + target.to_bytes(4,"little")
    s=0
    while True:
        i = MEM.find(pat, s)
        if i<0: break
        va = BASE+i
        # disassemble forward 0x30 bytes
        code = MEM[off_of(va):off_of(va)+0x30]
        fwd = [f"{x.address:08x}  {x.mnemonic} {x.op_str}" for x in md.disasm(code, va)]
        # look for store to [reg] : 'or byte [eXX], 4' / 'and ... fb' / 'mov byte [eXX], imm'
        for ln in fwd:
            if ("or byte" in ln and "4" in ln) or ("and byte" in ln and "fb" in ln) or ("mov byte" in ln):
                if f"e{['a','c','d','b','s','b','s','d'][reg]}" in ln or f"{['ax','cx','dx','bx','sp','bp','si','di'][reg]}" in ln:
                    writes.append((va, reg, fwd))
                    break
        s = i+1

with open(r"F:/Games/Taikou 2/scripts/_castleflag_w.txt", "w", encoding="utf-8") as f:
    f.write(f"=== 0x516638 载入寄存器后写入点: {len(writes)} ===\n")
    for va, reg, fwd in writes:
        f.write(f"\n@ {va:08x} load into e{['a','c','d','b','s','b','s','d'][reg]}:\n")
        f.write("\n".join(fwd[:12]) + "\n")

print(f"[OK ] candidate writers: {len(writes)}")
