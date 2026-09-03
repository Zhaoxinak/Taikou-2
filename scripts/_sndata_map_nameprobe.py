# -*- coding: utf-8 -*-
"""续227 修正：0x462fd0 依赖运行期 std::map(0x5152d0)，非静态二分。
本脚本：(1) 找全镜像对 0x5152d0 的 xref（定位 map 填充/使用点）；(2) dump 各候选名表基址原始字节，判结构。"""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from _disasm_all import disasm_all, load_image, BASE
import struct

MEM = load_image()
N = len(MEM)

def va2off(va):
    return va - BASE

def find_pattern(pat):
    """pat: bytes. 返回所有文件偏移。"""
    res = []
    start = 0
    while True:
        i = MEM.find(pat, start)
        if i < 0:
            break
        res.append(i)
        start = i + 1
    return res

# (1) xref to 0x5152d0 (小端 d0 52 51 00)
print("===== xref: 0x5152d0 (map this-ptr) =====")
refs = find_pattern(b"\xd0\x52\x51\x00")
print(f"  出现 {len(refs)} 处；换算 VA：")
for off in refs:
    va = off + BASE
    print(f"    off=0x{off:x}  va=0x{va:x}")

# (2) dump 候选名表基址
BASES = [0x504938, 0x504941, 0x50494a, 0x504953, 0x50495c, 0x504965,
         0x504a38, 0x504a41, 0x504a4a, 0x504a52, 0x504a5b, 0x504a64]
print()
print("===== 各候选名表基址前 64 字节 (hex) =====")
for b in BASES:
    off = va2off(b)
    raw = MEM[off:off+64]
    hexs = " ".join(f"{x:02x}" for x in raw)
    # 尝试按 u16 LE 解释
    u16s = struct.unpack("<32H", raw[:64])
    nums = " ".join(f"{v:04x}" for v in u16s[:16])
    print(f"  0x{b:06x}: {hexs}")
    print(f"           u16: {nums}")
