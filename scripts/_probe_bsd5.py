# -*- coding: utf-8 -*-
"""① 解码 0x507b58 技能名表  ② 找技能位域 getter (引用 +0xf/+0x10/+0x11)。"""
import re
from collections import Counter, defaultdict
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
mem = open(MEM_PATH, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

print("=" * 78)
print("A. 0x507b58 起的 50 字节 (5B×10 技能名表?)")
print("=" * 78)
for base in (0x507B58, 0x50C3CC, 0x507FDC):
    raw = mem[base - BASE: base - BASE + 60]
    print(f"\n  {base:#x}: " + " ".join(f"{x:02x}" for x in raw[:50]))
    # 按 5B 切
    parts = [raw[i:i + 5] for i in range(0, 50, 5)]
    for i, p in enumerate(parts):
        try:
            s = p.split(b"\x00")[0].decode("gbk")
        except Exception:
            s = p.decode("gbk", "replace")
        print(f"    [{i}] {p.hex()}  {s!r}")

print("\n" + "=" * 78)
print("B. 全镜像: 谁同时引用 byte[reg+0xf] / [reg+0x10] / [reg+0x11]")
print("=" * 78)
GEN = {"eax", "ecx", "edx", "ebx", "esi", "edi"}
# 先收集全部指令, 避免嵌套 disasm 破坏生成器
INS = []
o = 0
while o < len(mem) - 1:
    got = False
    for ins in md.disasm(mem[o:o + 4096], BASE + o):
        INS.append((ins.address, ins.mnemonic, ins.op_str, ins.size))
        got = True
        o_last = ins.address - BASE + ins.size
    if not got:
        o += 1
    else:
        o = o_last
print(f"  收集指令 {len(INS)} 条")

refs = defaultdict(set)   # disp -> {addr}
pat = re.compile(r"(\w+)?\s*ptr\s*\[(\w+)(?:\s*([+-])\s*(0x[0-9a-f]+))?\]")
for addr, mn, ops, sz in INS:
    for m in pat.finditer(ops):
        reg = m.group(2)
        if reg not in GEN:
            continue
        if not m.group(3):
            continue
        sign = 1 if m.group(3) == "+" else -1
        dv = sign * int(m.group(4), 16)
        if dv in (0xF, 0x10, 0x11):
            refs[dv].add(addr)

allthree = refs[0xF] & refs[0x10] & refs[0x11]
print(f"  +0xf: {len(refs[0xF])} 处, +0x10: {len(refs[0x10])} 处, +0x11: {len(refs[0x11])} 处")
print(f"  同一地址同时命中三者: {len(allthree)}")

# 按函数分组: 用 call 目标近似函数起点(简化: 按地址聚类)
def func_addrs():
    """所有 call rel32 目标 + jmp 目标 作为函数起点候选"""
    import struct
    s = set()
    for a, mn, ops, sz in INS:
        if mn == "call" and ops.startswith("0x"):
            try:
                s.add(int(ops, 16))
            except ValueError:
                pass
    return s

starts = sorted(func_addrs())
print(f"  函数起点候选 {len(starts)} 个")


def owner(addr):
    lo, hi = 0, len(starts) - 1
    best = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if starts[mid] <= addr:
            best = starts[mid]
            lo = mid + 1
        else:
            hi = mid - 1
    return best


byfunc = Counter()
for a in refs[0xF] | refs[0x10] | refs[0x11]:
    f = owner(a)
    if f:
        byfunc[f] += 1

print("\n  引用 +0xf/+0x10/+0x11 最多的函数 (前 12):")
for f, n in byfunc.most_common(12):
    tags = []
    for dv in (0xF, 0x10, 0x11):
        cnt = sum(1 for a in refs[dv] if owner(a) == f)
        if cnt:
            tags.append(f"+0x{dv:x}×{cnt}")
    print(f"    {f:#010x}  n={n:<4} {' '.join(tags)}")

print("\n" + "=" * 78)
print("C. 候选技能 getter / packer 反汇编")
print("=" * 78)
cands = [f for f, n in byfunc.most_common(8)]
for f in cands[:6]:
    print(f"\n--- {f:#010x} ---")
    o = f - BASE
    n = 0
    for ins in md.disasm(mem[o:o + 900], f):
        print(f"  {ins.address:08x}  {ins.mnemonic:<8} {ins.op_str}")
        n += 1
        if ins.mnemonic == "ret" or n > 60:
            break
