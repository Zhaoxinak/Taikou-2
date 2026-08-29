import sys

BIN = r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin"

def main():
    data = open(BIN, "rb").read()
    off = 0x506ca8 - 0x400000
    buf = data[off:off+9000]
    n = len(buf)
    strings = []
    i = 0
    while i < n:
        c = buf[i]
        if c == 0:
            i += 1
            continue
        if (0x20 <= c < 0x7f) or (0x81 <= c <= 0xfe):
            j = i
            raw = bytearray()
            while j < n and buf[j] != 0:
                b0 = buf[j]
                if 0x20 <= b0 < 0x7f:
                    raw.append(b0); j += 1
                elif 0x81 <= b0 <= 0xfe and j+1 < n and 0x40 <= buf[j+1] <= 0xfe:
                    raw.append(b0); raw.append(buf[j+1]); j += 2
                else:
                    break
            if len(raw) >= 2:
                strings.append(bytes(raw).decode("gbk", "replace"))
            i = j + 1
        else:
            i += 1
    print(f"total={len(strings)}")
    print("--- provinces 0..10 ---")
    for idx in range(0, min(11, len(strings))):
        print(f"  [{idx}] {strings[idx]}")
    print("--- types 292..369 ---")
    for idx in range(292, min(370, len(strings))):
        print(f"  [{idx}] {strings[idx]}")

main()
