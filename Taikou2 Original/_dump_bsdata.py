import struct

b = open("BSDATA1.TR2", "rb").read()
print("size", len(b))

# dump first 0x1C0 bytes, 16 per line, with offset
print("\n=== first 0x1C0 bytes ===")
for off in range(0, 0x1C0, 16):
    chunk = b[off:off+16]
    hexs = " ".join(f"{x:02X}" for x in chunk)
    asc = "".join(chr(x) if 32 <= x < 127 else "." for x in chunk)
    print(f"{off:04X}: {hexs:<48} {asc}")

# find all 武 (CE E4) and 、(AC A3) / 。(A1 A3) occurrences, dump context
def ctx(needle, label):
    print(f"\n=== context around {label} ({needle.hex()}) ===")
    start = 0
    n = 0
    while True:
        p = b.find(needle, start)
        if p < 0 or n >= 8:
            break
        lo = max(0, p-12); hi = min(len(b), p+20)
        chunk = b[lo:hi]
        hexs = " ".join(f"{x:02X}" for x in chunk)
        print(f"  @{p:04X}: ...{hexs}...")
        start = p + 1
        n += 1

ctx(b"\xce\xe4", "武")
ctx(b"\xac\xa3", "、")
ctx(b"\xa1\xa3", "。")

# Try to find name-like runs: sequences of bytes all >=0x80 (KOEI 2-byte codes)
# A name is typically several 2-byte codes. Scan for runs of >=2 consecutive
# BE 2-byte codes where both bytes >=0x80, and show them.
print("\n=== candidate KOEI 2-byte runs (both bytes >=0x80) ===")
i = 0
shown = 0
while i < len(b) - 1 and shown < 30:
    if b[i] >= 0x80 and b[i+1] >= 0x80:
        # extend run
        j = i
        codes = []
        while j < len(b)-1 and b[j] >= 0x80 and b[j+1] >= 0x80:
            codes.append((b[j] << 8) | b[j+1])
            j += 2
        if len(codes) >= 2:
            print(f"  @{i:04X}: " + " ".join(f"{c:04X}" for c in codes))
            shown += 1
        i = j
    else:
        i += 1
