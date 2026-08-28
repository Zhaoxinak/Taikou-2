#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""改进版 xref: 同时扫描 imm 与 mem.disp 对 字符串/文件表区 的引用。
聚焦: 文件表区 [0x506000,0x50D000] 的直接(基址)访问 -> 定位各分类文件表的加载函数入口。"""
import re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_IMM, CS_OP_MEM

BASE = 0x400000
DUMP = r"scripts/_unpacked_mem.bin"
OUT = r"scripts/_engine_xref2.txt"

data = open(DUMP, "rb").read()
SIZE = len(data)

# 所有 ASCII 串 VA -> 文本
str_map = {}
for m in re.finditer(rb"[ -~]{4,}", data):
    str_map[BASE + m.start()] = m.group().decode("latin1")

# 关键 target 的 VA
KEY_TARGETS = {
    "SNDATA1.TR2": b"SNDATA1.TR2", "TAIKOU2_SCENARIO": b"TAIKOU2_SCENARIO",
    "HJMAPDAT.DAT": b"HJMAPDAT.DAT", "HBMAP.LZW": b"HBMAP.LZW", "HKMAP.LZW": b"HKMAP.LZW",
    "HBOBJ.DAT": b"HBOBJ.DAT", "EXTFACE.PK8": b"EXTFACE.PK8", "NPKDATA.IDX": b"NPKDATA.IDX",
    "GRPDATA.LZW": b"GRPDATA.LZW", "TOWNMAP.LZW": b"TOWNMAP.LZW", "KOU2_SAVEFILE": b"KOU2_SAVEFILE",
}
key_va = {}
for name, b in KEY_TARGETS.items():
    for off in (m.start() for m in re.finditer(re.escape(b), data)):
        key_va[BASE + off] = name

FILETBL_LO, FILETBL_HI = 0x506000, 0x50D000

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

str_refs = []          # (iva, strva, text, iskey, keyname)
filetbl_refs = {}      # disp -> [iva,...]  直接(基址)访问文件表区的指令
addr = BASE + 0x1000
n = 0
while addr < BASE + SIZE:
    chunk = data[addr - BASE: addr - BASE + 64]
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
    for op in ins.operands:
        if op.type == CS_OP_IMM:
            v = op.imm & 0xFFFFFFFF
            if v in str_map:
                str_refs.append((ins.address, v, str_map[v], v in key_va, key_va.get(v, "")))
            if FILETBL_LO <= v <= FILETBL_HI and v in str_map:
                filetbl_refs.setdefault(v, []).append(ins.address)
        elif op.type == CS_OP_MEM:
            v = op.mem.disp & 0xFFFFFFFF
            if v in str_map:
                str_refs.append((ins.address, v, str_map[v], v in key_va, key_va.get(v, "")))
            if FILETBL_LO <= v <= FILETBL_HI and v in str_map:
                filetbl_refs.setdefault(v, []).append(ins.address)
    addr += ins.size
    n += 1

print(f"[*] scanned {n} instrs; str_refs={len(str_refs)}; filetbl direct-access VA={len(filetbl_refs)}")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("# 文件表区直接(基址)访问 xref\n")
    f.write(f"# region [{FILETBL_LO:#x},{FILETBL_HI:#x}]  共 {len(filetbl_refs)} 个被直接引用的字符串/表项\n\n")
    for disp in sorted(filetbl_refs):
        txt = str_map.get(disp, "?")
        f.write(f"\n### 表项 VA={disp:#010x}  '{txt[:70]}'  被 {len(filetbl_refs[disp])} 处访问\n")
        for iva in filetbl_refs[disp][:30]:
            f.write(f"    {iva:#010x}\n")

    # 关键 target 的引用 (含 mem.disp)
    f.write("\n\n" + "="*70 + "\n")
    f.write("## 关键 target 引用 (imm 或 mem.disp)\n")
    f.write("="*70 + "\n\n")
    keyrefs = [r for r in str_refs if r[3]]
    for kname in KEY_TARGETS:
        refs = [r for r in keyrefs if r[4] == kname]
        if not refs:
            f.write(f"\n### '{kname}': 无直接引用 (走间接/数据表遍历)\n")
            continue
        f.write(f"\n### '{kname}' ({len(refs)} 处)\n")
        for (iva, sva, txt, _, _) in refs:
            f.write(f"    {iva:#010x} -> '{txt[:50]}'\n")

print(f"[*] written: {OUT}")
