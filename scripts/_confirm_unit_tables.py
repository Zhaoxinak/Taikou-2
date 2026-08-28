#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
确认两块候选静态表的语义：
  - 0x52d211  (stride 8, 34 条)  疑似兵种/阵形/计略定义表
  - 0x501e48  (stride 48, 16 条) 疑似 16 级单位属性曲线表

做法：
  1) 在脱壳镜像中搜索两个地址的 32-bit 立即数（小端字节序），找到引用它们的代码位置。
  2) 对每个引用点用 capstone 反汇编上下文（前后若干指令），看是 mov/lea/cmp 等什么用途。
  3) 把两块表完整 dump 出来，按 stride 切片做成结构化预览。
"""
import struct, sys

try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
except ImportError:
    print("capstone 未安装；部分功能跳过")
    Cs = None

BIN = "scripts/_unpacked_mem.bin"
BASE = 0x400000  # 镜像加载基址

def le_bytes(addr):
    return struct.pack("<I", addr)

def load():
    with open(BIN, "rb") as f:
        return f.read()

def find_xrefs(data, addr):
    """返回所有出现 addr 作为 32-bit 立即数的文件偏移 + 虚拟地址。"""
    pat = le_bytes(addr)
    hits = []
    start = 0
    while True:
        i = data.find(pat, start)
        if i < 0:
            break
        hits.append(BASE + i)
        start = i + 1
    return hits

def disasm_context(data, vaddr, before=12, after=14):
    """从 vaddr 反汇编上下文。"""
    if Cs is None:
        return []
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    off = vaddr - BASE
    if off < 0 or off >= len(data):
        return []
    # 从 before*4 之前开始反汇编，取足够多指令
    ctx_start = max(0, off - before * 6)
    chunk = data[ctx_start: off + after * 6 + 40]
    out = []
    for ins in md.disasm(chunk, BASE + ctx_start):
        if ins.address >= vaddr - before * 6 and ins.address <= vaddr + after * 6:
            out.append((ins.address, ins.bytes.hex(), ins.mnemonic + " " + ins.op_str))
        if ins.address > vaddr + after * 6:
            break
    return out

def dump_table(data, vaddr, stride, n):
    off = vaddr - BASE
    recs = []
    for r in range(n):
        base = off + r * stride
        if base + stride > len(data):
            break
        raw = data[base: base + stride]
        vals_u8 = list(raw)
        # 尝试当 word 解释
        vals_u16 = [struct.unpack("<H", raw[i:i+2])[0] for i in range(0, len(raw)-1, 2)]
        recs.append({"rec": r, "raw_hex": raw.hex(), "u8": vals_u8, "u16_le": vals_u16})
    return recs

def main():
    data = load()
    print(f"镜像大小: {len(data)} B (0x{len(data):x})")

    targets = [0x52d211, 0x501e48]
    for t in targets:
        print("\n" + "=" * 78)
        print(f"目标地址 0x{t:08x}  小端字节序 = {le_bytes(t).hex()}")
        hits = find_xrefs(data, t)
        print(f"  作为 32-bit 立即数出现的次数: {len(hits)}")
        for h in hits:
            print(f"\n  >>> 引用点 VA=0x{h:08x}")
            ctx = disasm_context(data, h)
            for va, bhex, s in ctx:
                mark = "  <== 命中" if va == h else ""
                print(f"    0x{va:08x}  {bhex:<20} {s}{mark}")

    # 详细 dump 两块表
    print("\n" + "=" * 78)
    print("详细 dump: 0x52d211 (stride 8)")
    t1 = dump_table(data, 0x52d211, 8, 40)
    for r in t1:
        print(f"  [{r['rec']:2d}] u8={r['u8']}  hex={r['raw_hex']}")

    print("\n" + "=" * 78)
    print("详细 dump: 0x501e48 (stride 48)")
    t2 = dump_table(data, 0x501e48, 48, 20)
    for r in t2:
        print(f"  [{r['rec']:2d}] hex={r['raw_hex'][:96]}{'...' if len(r['raw_hex'])>96 else ''}")
        print(f"        u8={r['u8']}")

if __name__ == "__main__":
    main()
