# -*- coding: utf-8 -*-
"""解码能力名表 (0x507fc0 起 stride 7)。"""
MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
mem = open(MEM_PATH, "rb").read()

print("=== 0x507fb0..0x508000 原始 ===")
for i in range(0x507FB0, 0x508000, 16):
    print(f"  {i:08x}: " + " ".join(f"{x:02x}" for x in mem[i - BASE:i - BASE + 16]))

print("\n=== 按 stride 7 从各起点解码 (找 5 连能力名) ===")
for start in range(0x507F80, 0x507FF0):
    vals = []
    ok = True
    for k in range(5):
        seg = mem[start - BASE + 7 * k: start - BASE + 7 * k + 7]
        s = seg.split(b"\x00")[0]
        try:
            d = s.decode("gbk")
        except Exception:
            ok = False
            break
        if not d or len(d) < 2:
            ok = False
            break
        vals.append(d)
    if ok:
        print(f"  {start:#010x} stride7: {vals}")

print("\n=== 直接列 0x507fb0..0x507fe0 每 7 字节 ===")
for i in range(0x507FB0, 0x507FE8, 7):
    seg = mem[i - BASE:i - BASE + 7]
    print(f"  {i:08x}: {seg.hex()}  {seg.split(b'\x00')[0].decode('gbk','replace')!r}")
