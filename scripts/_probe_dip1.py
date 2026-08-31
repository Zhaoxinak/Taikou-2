# -*- coding: utf-8 -*-
"""
_probe_dip1.py — 外交「关系值变更公式/成功率」追查 第1步
扫描全映像中对以下绝对地址的引用（modrm disp32 / imm32 均为原始小端字节）:
    0x525ea4  使者槽 dword
    0x5080cc  8 级国关系表（续89 称无 xref）
    0x5179b8  国政治表 stride 14 x 49
并反汇编命中点所在函数。
"""
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
MEM = open(MEM_PATH, "rb").read()
SZ = len(MEM)

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def off2va(o):
    return BASE + o


def va2off(va):
    return va - BASE


def rd(va, n):
    o = va2off(va)
    if o < 0 or o + n > SZ:
        return b""
    return MEM[o:o + n]


def find_abs_refs(va):
    """全映像搜索 va 的小端 4 字节，返回所有命中偏移。"""
    pat = struct.pack("<I", va)
    out = []
    i = MEM.find(pat)
    while i != -1:
        out.append(i)
        i = MEM.find(pat, i + 1)
    return out


def func_start(o):
    """向上回溯找函数入口：连续的 CC/RET 或对齐 padding 之后。"""
    limit = max(0, o - 0x400)
    i = o
    # 向上找最近的 ret (c3 / c2 xx xx) 或 int3 块
    while i > limit:
        b = MEM[i]
        if b == 0xC3:
            return i + 1
        if b == 0xC2 and i + 2 < SZ:
            return i + 3
        i -= 1
    return limit


def disasm(va, n=70):
    o = va2off(va)
    if o < 0:
        return f"  [bad va {va:#x}]"
    lines = []
    for ins in md.disasm(MEM[o:o + n * 8], va):
        lines.append(f"  {ins.address:#x}  {ins.mnemonic:<8} {ins.op_str}")
        if len(lines) >= n:
            break
        if ins.mnemonic == "ret":
            break
    return "\n".join(lines) if lines else "  [disasm empty]"


TARGETS = [
    (0x525EA4, "使者槽 dword (messenger slot)"),
    (0x5080CC, "8 级国关系表"),
    (0x5179B8, "国政治表 stride14 x49"),
    (0x525EA8, "0x525ea8 计数器 word"),
    (0x525E58, "0x525e58 标志"),
]

for va, name in TARGETS:
    hits = find_abs_refs(va)
    print("=" * 78)
    print(f"### {name}  {va:#x}  ->  {len(hits)} 处绝对引用")
    print("=" * 78)
    if not hits:
        print("  (无)")
        continue
    # 按所属函数分组
    funcs = {}
    for h in hits:
        fs = func_start(h)
        funcs.setdefault(fs, []).append(h)
    for fs in sorted(funcs):
        hs = funcs[fs]
        print(f"\n--- 函数 {off2va(fs):#x}  (命中 {len(hs)} 处: "
              f"{', '.join(hex(off2va(h)) for h in hs)}) ---")
        # 从函数头开始反汇编，覆盖到最后一个命中 +0x40
        span = max(hs) - fs + 0x40
        o = fs
        for ins in md.disasm(MEM[o:o + min(span, 0x600)], off2va(fs)):
            mark = "  <<<" if off2va(hs[0]) <= ins.address <= off2va(max(hs)) else ""
            star = " *" if any(off2va(h) <= ins.address < off2va(h) + 8 for h in hs) else "  "
            print(f"  {star}{ins.address:#x}  {ins.mnemonic:<8} {ins.op_str}{mark}")
            if ins.mnemonic == "ret":
                break
    print()
