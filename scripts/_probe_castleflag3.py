MEM = open(r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin", "rb").read()
BASE = 0x400000
def find_pat(pat):
    out=[]; s=0
    while True:
        i = MEM.find(pat, s)
        if i<0: break
        out.append(BASE+i); s=i+1
    return out

addr = 0x516638
a = addr.to_bytes(4, "little")

# store forms
patterns = {
    "mov [addr],al (a2)": b'\xa2'+a,
    "mov [addr],eax (a3)": b'\xa3'+a,
    "mov [addr],al (88 05)": b'\x88\x05'+a,
    "or  [addr],imm (80 0c 25)": b'\x80\x0c\x25'+a,   # SIB form
    "and [addr],imm (80 24 25)": b'\x80\x24\x25'+a,   # SIB form
    "mov [addr],imm32 (c7 05)": b'\xc7\x05'+a,
}
with open(r"F:/Games/Taikou 2/scripts/_castleflag_store.txt", "w", encoding="utf-8") as f:
    f.write(f"=== 0x516638 store-form search ===\n")
    for name, pat in patterns.items():
        hits = find_pat(pat)
        f.write(f"{name}: {len(hits)} -> {[f'{x:08x}' for x in hits]}\n")
        print(f"{name}: {hits}")
