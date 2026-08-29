from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin", "rb").read()
BASE = 0x400000
def off_of(va): return va - BASE

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

for va in (0x45f0d5, 0x45f0c0):  # writers of 0x513ff6/0x513ff8 (search 0x513ff8 too)
    pass

# find 0x513ff8 writer
def find_writer(addr):
    a = addr.to_bytes(4, "little")
    for pre in (b'\x66\xc7\x05',):
        pat = pre + a
        i = MEM.find(pat)
        if i >= 0:
            return BASE + i
    return None

for addr in (0x513ff6, 0x513ff8):
    w = find_writer(addr)
    print(f"writer of {addr:08x} = {w:08x}" if w else f"writer of {addr:08x} = NONE")
    if w:
        off = off_of(w)
        code = MEM[off-0x60:off+0x40]
        lines = [f"{ins.address:08x}  {ins.mnemonic} {ins.op_str}" for ins in md.disasm(code, w-0x60)]
        with open(f"F:/Games/Taikou 2/scripts/_flagw_{addr:x}.txt", "w", encoding="utf-8") as f:
            f.write(f"=== writer of {addr:08x} @ {w:08x} (context) ===\n")
            f.write("\n".join(lines))
        print(f"  -> wrote _flagw_{addr:x}.txt")
