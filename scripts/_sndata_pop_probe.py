# -*- coding: utf-8 -*-
"""续227: (a) 反汇编 0x46e2a5(SNDATA 处理入口, 0x4624f0 的唯一调用方)；
(b) 搜全镜像中加载 map 指针的指令 (mov ecx,[0x48c3b7] / [0x478b41]) 以定位填充点。"""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from _disasm_all import disasm_all, load_image, BASE

MEM = load_image()
def va2off(va): return va - BASE
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False

print("===== 0x46e2a5..0x46e480 (SNDATA 处理入口) =====")
for ins in disasm_all(md, MEM[va2off(0x46e2a5):va2off(0x46e480)], 0x46e2a5):
    print(f"  {ins.address:#010x}  {ins.bytes.hex():20s} {ins.mnemonic} {ins.op_str}")

# (b) 搜加载 map 指针的数据引用
print()
print("===== xref: 加载 map 指针 (mov ecx,[0x48c3b7]=8b0db7c34800 / mov ecx,[0x478b41]=8b0d418b4700) =====")
for pat, name in [(b"\x8b\x0d\xb7\xc3\x48\x00", "mov ecx,[0x48c3b7]"),
                  (b"\x8b\x0d\x41\x8b\x47\x00", "mov ecx,[0x478b41]"),
                  (b"\xa1\xb7\xc3\x48\x00", "mov eax,[0x48c3b7]"),
                  (b"\x8b\x35\xb7\xc3\x48\x00", "mov esi,[0x48c3b7]")]:
    res = []
    start = 0
    while True:
        i = MEM.find(pat, start)
        if i < 0: break
        res.append(i + BASE)
        start = i + 1
    print(f"  {name}: {[hex(x) for x in res]}")
