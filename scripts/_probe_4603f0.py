from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin", "rb").read()
BASE = 0x400000
def off_of(va): return va - BASE
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

def dis(va, n):
    code = MEM[off_of(va):off_of(va)+n]
    return [f"{i.address:08x}  {i.mnemonic} {i.op_str}" for i in md.disasm(code, va)]

for label, va, n in [
    ("0x4603f0 dispatcher", 0x4603f0, 0x120),
    ("0x49f6b0 ID source", 0x49f6b0, 0x80),
    ("0x4ebe40 predicate(0x28)", 0x4ebe40, 0x80),
]:
    lines = dis(va, n)
    with open(f"F:/Games/Taikou 2/scripts/_d_{va:x}.txt", "w", encoding="utf-8") as f:
        f.write(f"=== {label} @ {va:08x} ===\n" + "\n".join(lines))
    print(f"[OK ] {label}: {len(lines)} instrs")
