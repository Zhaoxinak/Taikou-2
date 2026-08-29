#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TAIK2W95 脱壳后引擎静态分析器
- 全量线性反汇编 _unpacked_mem.bin (VA 基址 0x400000)
- 收集所有 ASCII 字符串的 VA -> 文本
- 扫描所有 "指令立即数 == 某字符串起始 VA" 的 xref (即代码引用数据文件名/常量的点)
- 对每个 xref，反汇编其前后上下文，按被引用字符串分组输出到 _engine_xref.txt
- 重点标注关键 target (SNDATA/SCENARIO/HJMAPDAT 等)
"""
import re, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_IMM

BASE = 0x400000
DUMP = r"scripts/_unpacked_mem.bin"
OUT = r"scripts/_engine_xref.txt"

data = open(DUMP, "rb").read()
SIZE = len(data)
mem_end = BASE + SIZE  # 0x600000

# 1) 收集所有 ASCII 字符串 (>=4) 的 VA -> 文本
str_map = {}  # va -> text
for m in re.finditer(rb"[ -~]{4,}", data):
    off = m.start()
    va = BASE + off
    str_map[va] = m.group().decode("latin1")

print(f"[*] dump={SIZE} bytes, strings found={len(str_map)}")

# 2) 线性反汇编
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

KEY_TARGETS = {
    "SNDATA1.TR2": b"SNDATA1.TR2",
    "TAIKOU2_SCENARIO": b"TAIKOU2_SCENARIO",
    "HJMAPDAT.DAT": b"HJMAPDAT.DAT",
    "HBMAP.LZW": b"HBMAP.LZW",
    "HKMAP.LZW": b"HKMAP.LZW",
    "HBOBJ.DAT": b"HBOBJ.DAT",
    "EXTFACE.PK8": b"EXTFACE.PK8",
    "NPKDATA.IDX": b"NPKDATA.IDX",
    "GRPDATA.LZW": b"GRPDATA.LZW",
    "TOWNMAP.LZW": b"TOWNMAP.LZW",
    "KOU2_SAVEFILE": b"KOU2_SAVEFILE",
}

# 预先计算每个 key target 的 VA
key_va = {}
for name, b in KEY_TARGETS.items():
    for off in (m.start() for m in re.finditer(re.escape(b), data)):
        key_va[BASE + off] = name

xrefs = []  # (ins_va, str_va, str_text, is_key, key_name)
addr = BASE + 0x1000  # 从 0x401000 起 (跳过 MZ/PE 头区, 那是数据)
while addr < mem_end:
    chunk = data[addr - BASE : addr - BASE + 64]
    if not chunk:
        break
    try:
        ins = next(md.disasm(chunk, addr))
    except StopIteration:
        addr += 1
        continue
    if ins is None:
        addr += 1
        continue
    # 检查立即数操作数
    for op in ins.operands:
        if op.type == CS_OP_IMM:
            imm = op.imm & 0xFFFFFFFF
            if imm in str_map:
                is_key = imm in key_va
                xrefs.append((ins.address, imm, str_map[imm], is_key, key_va.get(imm, "")))
    addr += ins.size

print(f"[*] xref scan done, total refs={len(xrefs)}, key refs={sum(1 for x in xrefs if x[3])}")

# 3) 输出: 对每个 xref 反汇编前后上下文
def disasm_ctx(center_va, before=0x180, after=0x280):
    """反汇编 center_va 前后一段，返回文本行列表"""
    lines = []
    a = center_va
    # 向前找起点
    start = max(BASE + 0x1000, center_va - before)
    # 减少输出量：以 center 为中心，固定窗口反汇编
    chunk = data[start - BASE : center_va + after - BASE]
    if not chunk:
        return lines
    for ins in md.disasm(chunk, start):
        if ins.address > center_va + after:
            break
        mark = " >>" if ins.address == center_va else "   "
        lines.append(f"{mark}{ins.address:#010x}  {ins.mnemonic} {ins.op_str}")
    return lines

key_xrefs = [x for x in xrefs if x[3]]
normal_xrefs = [x for x in xrefs if not x[3]]

with open(OUT, "w", encoding="utf-8") as f:
    f.write("# TAIK2W95 脱壳后引擎 xref 分析报告\n")
    f.write(f"# dump: {DUMP} ({SIZE} bytes), VA base 0x{BASE:08x}\n")
    f.write(f"# 总 xref={len(xrefs)}, 关键 xref={len(key_xrefs)}\n\n")

    f.write("="*70 + "\n")
    f.write(f"## 关键 xref (KEY) — {len(key_xrefs)} 个\n")
    f.write("="*70 + "\n\n")
    # 按 key_name 分组
    by_key = {}
    for x in key_xrefs:
        by_key.setdefault(x[4], []).append(x)
    for kname in KEY_TARGETS:
        if kname not in by_key:
            continue
        f.write(f"\n### 引用 '{kname}' 的代码 ({len(by_key[kname])} 处)\n")
        for (iva, sva, stext, _, _) in by_key[kname]:
            f.write(f"\n--- 调用点 ins @ {iva:#010x}  (引用字符串 @ {sva:#010x}: '{stext[:60]}')\n")
            ctx = disasm_ctx(iva)
            f.write("\n".join(ctx) + "\n")

    f.write("\n\n" + "="*70 + "\n")
    f.write(f"## 普通 xref (NON-KEY, 前 120 个)\n")
    f.write("="*70 + "\n\n")
    for (iva, sva, stext, _, _) in normal_xrefs[:120]:
        f.write(f"{iva:#010x} -> '{stext[:50]}'  ({sva:#010x})\n")

    # 统计: 哪些字符串被引用得最多
    f.write("\n\n" + "="*70 + "\n")
    f.write("## 被引用次数最多的字符串 TOP 40\n")
    f.write("="*70 + "\n\n")
    from collections import Counter
    cnt = Counter(s[2] for s in xrefs)
    for txt, n in cnt.most_common(40):
        f.write(f"  {n:4}x  {txt[:70]}\n")

print(f"[*] written: {OUT}")
