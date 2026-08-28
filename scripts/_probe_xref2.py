MEM = open(r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin", "rb").read()

def find_addr_refs(addr, opcodes):
    """Find instructions referencing absolute [addr] via given opcode prefixes.
    addr: 32-bit value. opcodes: list of byte prefixes, e.g. [b'\x66\x83\x3d'] (cmp word [...],0)."""
    import struct
    a = struct.pack("<I", addr)
    hits = []
    for pre in opcodes:
        pat = pre + a
        start = 0
        while True:
            i = MEM.find(pat, start)
            if i < 0:
                break
            hits.append((0x400000 + i, pre.hex()))
            start = i + 1
    return sorted(hits)

# Absolute [0x513ff6] and [0x513ff8] references
for addr in (0x513ff6, 0x513ff8):
    # cmp word ptr [addr], 0  -> 66 83 3d <addr>
    # cmp word ptr [addr], imm8 -> 66 83 3d <addr> <imm>  (also 66 81 3d for imm16)
    # mov word ptr [addr], ... -> 66 c7 05 <addr> (imm16) or 66 89 / 0d
    ops = [b'\x66\x83\x3d', b'\x66\x81\x3d', b'\x66\xc7\x05', b'\x66\x29\x0d',
           b'\x66\x01\x0d', b'\x66\x09\x0d', b'\x66\x31\x0d', b'\x66\x21\x0d']
    hits = find_addr_refs(addr, ops)
    with open(f"F:/Games/Taikou 2/scripts/_xref2_{addr:x}.txt", "w", encoding="utf-8") as f:
        f.write(f"=== refs to {addr:08x} ===\n")
        if not hits:
            f.write("(none)\n")
        for va, pre in hits:
            f.write(f"{va:08x}  {pre}\n")
    print(f"[OK ] {addr:08x}: {len(hits)} refs")
