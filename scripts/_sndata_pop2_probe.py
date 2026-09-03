# -*- coding: utf-8 -*-
"""续227: 定位 0x5152d0 map 的填充代码。
(1) dump 0x48c3b7 / 0x478b41 周围字节，确认是否是指向 map 的指针变量。
(2) 搜 'mov reg,[0x48c3b7]' / 'mov reg,[0x478b41]' 类指令，定位填充调用点。"""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from _disasm_all import disasm_all, load_image, BASE
import struct

MEM = load_image()
def va2off(va): return va - BASE
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False

def dump(va, n=32):
    raw = MEM[va2off(va):va2off(va)+n]
    hexs = " ".join(f"{x:02x}" for x in raw)
    vals = struct.unpack(f"<{n//4}I", raw)
    print(f"  @0x{va:x}: {hexs}")
    print(f"          u32: {' '.join(hex(v) for v in vals)}")

print("===== 数据引用点周围字节 =====")
print(" 0x48c3b7:"); dump(0x48c3b7)
print(" 0x478b41:"); dump(0x478b41)

print()
print("===== 搜索加载 map 指针变量的指令 =====")
pats = {
    "mov ecx,[0x48c3b7]": b"\x8b\x0d\xb7\xc3\x48\x00",
    "mov eax,[0x48c3b7]": b"\xa1\xb7\xc3\x48\x00",
    "mov edx,[0x48c3b7]": b"\x8b\x15\xb7\xc3\x48\x00",
    "mov esi,[0x48c3b7]": b"\x8b\x35\xb7\xc3\x48\x00",
    "mov ecx,[0x478b41]": b"\x8b\x0d\x41\x8b\x47\x00",
    "mov eax,[0x478b41]": b"\xa1\x41\x8b\x47\x00",
    "lea ecx,[0x48c3b7]": b"\x8d\x0d\xb7\xc3\x48\x00",
    "lea eax,[0x48c3b7]": b"\x8d\x05\xb7\xc3\x48\x00",
}
for name, pat in pats.items():
    res = []
    start = 0
    while True:
        i = MEM.find(pat, start)
        if i < 0: break
        res.append(i + BASE)
        start = i + 1
    if res:
        print(f"  {name}: {[hex(x) for x in res]}")
