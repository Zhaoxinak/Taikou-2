#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""反汇编两块候选表所在区域，确认是数据表还是代码/函数。"""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BIN = "scripts/_unpacked_mem.bin"
BASE = 0x400000

def load():
    with open(BIN, "rb") as f:
        return f.read()

def disasm(data, va_start, va_end):
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    off = va_start - BASE
    chunk = data[off: va_end - BASE]
    out = []
    for ins in md.disasm(chunk, va_start):
        out.append((ins.address, ins.bytes.hex(), ins.mnemonic + " " + ins.op_str))
    return out

def find_prologue_backward(data, va, max_back=0x200):
    """从 va 向前找函数 prologue（push ebp / mov ebp,esp 或 push esi;...）。"""
    off = va - BASE
    # 扫描候选 prologue 字节序列
    prologues = [
        b"\x55\x8b\xec",          # push ebp; mov ebp, esp
        b"\x55\x89\xe5",          # push ebp; mov ebp, esp (AT&T style, 同义)
        b"\x56\x57",              # push esi; push edi
        b"\x53\x56",              # push ebx; push esi
    ]
    best = None
    for i in range(0, max_back, 1):
        p = off - i
        if p < 0:
            break
        for pr in prologues:
            if data[p:p+len(pr)] == pr:
                cand = BASE + p
                if best is None or cand > best:
                    best = cand
    return best

def main():
    data = load()

    print("### 区域 A: 0x41bf20 函数（引用 0x501e48），反汇编 0x41bea0..0x41c220")
    a = disasm(data, 0x41bea0, 0x41c220)
    for va, bhex, s in a:
        print(f"  0x{va:08x}  {bhex:<22} {s}")

    print("\n### 区域 B: 0x52d211 附近，反汇编 0x52d1e0..0x52d3a0")
    b = disasm(data, 0x52d1e0, 0x52d3a0)
    for va, bhex, s in b:
        print(f"  0x{va:08x}  {bhex:<22} {s}")

    # 找包含 0x52d211 的函数起点
    print("\n### 0x52d211 前向 prologue 搜索（最多 0x300）")
    start = find_prologue_backward(data, 0x52d211, 0x300)
    print(f"  候选函数起点: 0x{start:08x}" if start else "  未找到 prologue")

    # 在整个镜像中搜索 0x52d211 表的标志性 marker：66 bb <digit> <digit>
    print("\n### 全镜像搜索 '66 bb' 出现次数与位置（判断表是否被引用/有几份）")
    cnt = 0
    positions = []
    pat = b"\x66\xbb"
    start_s = 0
    while True:
        i = data.find(pat, start_s)
        if i < 0:
            break
        cnt += 1
        if len(positions) < 20:
            positions.append(BASE + i)
        start_s = i + 1
    print(f"  '66 bb' 出现次数: {cnt}")
    print(f"  前若干位置 VA: {[hex(p) for p in positions]}")

    # 搜索 0x52d211 表内容的另一标志：rec[1] = 04 66 bb 30 31 (ascii "01")
    print("\n### 搜索 '04 66 bb 30 31'（0x52d211 rec1 标志）出现次数")
    cnt2 = 0
    s2 = 0
    while True:
        i = data.find(b"\x04\x66\xbb\x30\x31", s2)
        if i < 0:
            break
        cnt2 += 1
        s2 = i + 1
    print(f"  '04 66 bb 30 31' 出现次数: {cnt2}")

    # 搜索 0x52d211 表中反复出现的 8 字节结构 '04 66 bb' 后跟 ASCII 数字
    print("\n### 反汇编 0x52d211 起 0x60 字节（逐条确认是数据还是代码）")
    c = disasm(data, 0x52d211, 0x52d280)
    for va, bhex, s in c:
        print(f"  0x{va:08x}  {bhex:<22} {s}")

if __name__ == "__main__":
    main()
