# -*- coding: utf-8 -*-
"""① 确认 剑术 = byte[+0xf]>>6&3  ② 定位能力名表(统率/武力/内政/外交/魅力)。"""
import re
from collections import Counter
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
mem = open(MEM_PATH, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)

print("=" * 78)
print("A. 全镜像搜 byte[reg+0xf] 配合 shr 6 (剑术)")
print("=" * 78)
# 线性扫, 收集含 +0xf 且紧跟 shr x,6 的站点
o = 0
sites = []
while o < len(mem) - 1:
    last = None
    for ins in md.disasm(mem[o:o + 4096], BASE + o):
        last = ins.address - BASE + ins.size
        s = ins.op_str
        if "+ 0xf]" in s and "byte" in s:
            sites.append((ins.address, ins.mnemonic, s))
    o = last if last and last > o else o + 4096
print(f"  byte[reg+0xf] 站点 {len(sites)} 处")
# 打印附近含 shr 6 的
cnt = 0
for addr, mn, ops in sites:
    o2 = addr - BASE
    seq = []
    for ins in md.disasm(mem[o2:o2 + 24], addr):
        seq.append((ins.address, ins.mnemonic, ins.op_str))
        if len(seq) >= 4:
            break
    txt = " ; ".join(f"{m} {p}" for _, m, p in seq)
    if "shr" in txt and ", 6" in txt:
        print(f"    {addr:08x}  {txt}")
        cnt += 1
        if cnt > 8:
            break
if cnt == 0:
    print("    未找到直接 shr 6; 试用 and 0xc0 / rol / 高位访问")
    for addr, mn, ops in sites:
        o2 = addr - BASE
        seq = []
        for ins in md.disasm(mem[o2:o2 + 24], addr):
            seq.append((ins.address, ins.mnemonic, ins.op_str))
            if len(seq) >= 4:
                break
        txt = " ; ".join(f"{m} {p}" for _, m, p in seq)
        if "0xc0" in txt:
            print(f"    {addr:08x}  {txt}")

print("\n" + "=" * 78)
print("B. 能力名 GBK 串定位")
print("=" * 78)
for w in ("统率", "武力", "内政", "外交", "魅力", "剑术"):
    enc = w.encode("gbk")
    idxs = [m.start() for m in re.finditer(re.escape(enc), mem)]
    va = [hex(BASE + i) for i in idxs[:8]]
    print(f"  {w} ({enc.hex()}) x{len(idxs)}  {va}")

print("\n" + "=" * 78)
print("C. 0x507fdc 附近 32B (魅力) 与 0x50c3cc 附近 (外交) 上下文")
print("=" * 78)
for base in (0x507FDC, 0x50C3CC):
    raw = mem[base - BASE - 16: base - BASE + 40]
    print(f"  {base:#x}: ...{raw.hex()}")

print("\n" + "=" * 78)
print("D. 找能力名表: 扫描连续 5 个 3字节(2汉字+NUL) GBK 串")
print("=" * 78)
# 3B 组: 2 汉字 + 00
pat = re.compile(rb"(?:[\x81-\xfe][\x40-\xfe]){2}\x00")
runs = []
for m in pat.finditer(mem):
    runs.append(BASE + m.start())
# 找 5 连 (间距 3)
groups = []
for i in range(len(runs) - 4):
    if all(runs[i + k + 1] - runs[i + k] == 3 for k in range(4)):
        groups.append(runs[i])
uniq = []
for g in groups:
    if not uniq or g - uniq[-1] > 12:
        uniq.append(g)
print(f"  5 连 3B 中文串组: {len(uniq)} 处")
for g in uniq[:20]:
    vals = []
    for k in range(5):
        s = mem[g - BASE + 3 * k: g - BASE + 3 * k + 2].decode("gbk", "replace")
        vals.append(s)
    print(f"    {g:#010x}: {vals}")
