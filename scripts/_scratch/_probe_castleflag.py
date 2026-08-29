MEM = open(r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin", "rb").read()
BASE = 0x400000

def find_addr_refs(addr, opcodes):
    a = addr.to_bytes(4, "little")
    hits = []
    for pre in opcodes:
        pat = pre + a
        start = 0
        while True:
            i = MEM.find(pat, start)
            if i < 0:
                break
            hits.append((BASE + i, pre.hex()))
            start = i + 1
    return sorted(hits)

# 0x516638 castle-lord flag (bit2 = 0x04 -> 城主 display)
for addr in (0x516638,):
    ops = [
        b'\x80\x0d',   # or byte[addr], imm8
        b'\x80\x25',   # and byte[addr], imm8
        b'\xc6\x05',   # mov byte[addr], imm8
        b'\x80\x3d',   # cmp byte[addr], imm8
        b'\xf6\x05',   # test byte[addr], imm8
        b'\xa0',       # mov al, [addr]
        b'\x8a\x05',   # mov al, [addr] (alt)
    ]
    hits = find_addr_refs(addr, ops)
    with open(f"F:/Games/Taikou 2/scripts/_castleflag_{addr:x}.txt", "w", encoding="utf-8") as f:
        f.write(f"=== refs to {addr:08x} (城主/持城 flag) ===\n")
        if not hits:
            f.write("(none)\n")
        for va, pre in hits:
            f.write(f"{va:08x}  {pre}\n")
    print(f"[OK ] {addr:08x}: {len(hits)} refs")

# also: what sets the castle-lord via word? maybe word[0x516638]? unlikely. check 0x516638 as word:
for addr in (0x516638,):
    ops = [b'\x66\xc7\x05', b'\x66\x83\x0d', b'\x66\x81\x0d', b'\xc7\x05']
    hits = find_addr_refs(addr, ops)
    print(f"[word] {addr:08x}: {len(hits)} refs")
