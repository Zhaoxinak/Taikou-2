from capstone import Cs, CS_ARCH_X86, CS_MODE_32
MEM = open(r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin", "rb").read()
BASE = 0x400000
def off_of(va): return va - BASE
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

REND = 0x4e87e0
# find callers
calls = []
off = 0
while off < len(MEM)-8:
    for ins in md.disasm(MEM[off:off+0x4000], BASE+off):
        if ins.mnemonic=="call" and ins.op_str.lower()==f"0x{REND:x}":
            calls.append(ins.address)
    off += 0x4000

def dis_back(va, n=0x140):
    start = va-n
    return [f"{i.address:08x}  {i.mnemonic} {i.op_str}" for i in md.disasm(MEM[off_of(start):off_of(va)], start)]

with open(r"F:/Games/Taikou 2/scripts/_rendcall.txt", "w", encoding="utf-8") as f:
    f.write(f"=== callers of renderer 0x4e87e0: {len(calls)} ===\n")
    for ca in calls[:12]:
        bs = dis_back(ca)
        # look for 0x516638 setup: any 'or byte [..], 4' / 'and byte [..], 4' / 'mov byte [..], 4'
        flag = [l for l in bs if ("516638" in l) or ("or byte" in l and "4" in l) or ("and byte" in l and "4" in l)]
        f.write(f"\n--- caller @ {ca:08x} ---\n")
        f.write("\n".join(bs[-18:]) + "\n")
        if flag:
            f.write("  [FLAG-REL] " + " | ".join(flag[-3:]) + "\n")

print(f"[OK ] renderer callers={len(calls)} (dumped first 12)")
