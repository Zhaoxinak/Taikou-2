# -*- coding: utf-8 -*-
"""续227: 在镜像中定位 std::map(0x5152d0) 的 (id->name_base) 源表。
策略：搜 9 个 name_base 常量的 u32 出现位置，检查其上下文是否为 (u16 id, u32 name_base) 规则表。"""
from _disasm_all import load_image, BASE
import struct

MEM = load_image()
def va2off(va): return va - BASE

NAMES = {0x504938:"势0", 0x504941:"米D", 0x504a41:"米2", 0x504a38:"米3",
         0x504a4a:"米9", 0x50494a:"家2", 0x504953:"大3", 0x50495c:"持4", 0x504965:"属5"}

print("===== 各 name_base 常量出现位置 (文件偏移 / VA) =====")
for nb, lbl in NAMES.items():
    pat = struct.pack("<I", nb)
    res = []
    start = 0
    while True:
        i = MEM.find(pat, start)
        if i < 0: break
        res.append(i + BASE)
        start = i + 1
    print(f"  {lbl} (0x{nb:06x}): {len(res)} 处 -> {[hex(x) for x in res[:12]]}")

# 检查 0x504938 的某处是否 preceded by 小 u16（候选 (id,u32) 表）
print()
print("===== 0x504938 出现处前 6 字节（看是否 u16 id 前缀）=====")
pat = struct.pack("<I", 0x504938)
start = 0
cnt = 0
while cnt < 8:
    i = MEM.find(pat, start)
    if i < 0: break
    va = i + BASE
    pre = MEM[i-6:i]
    (prev_u16,) = struct.unpack("<H", pre[0:2]) if i>=2 else (0,)
    (prev_u32,) = struct.unpack("<I", pre[2:6]) if i>=4 else (0,)
    print(f"  va=0x{va:x}: pre6={pre.hex()}  prev_u16=0x{prev_u16:x} prev_u32=0x{prev_u32:x}")
    start = i + 1
    cnt += 1
