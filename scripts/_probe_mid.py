# -*- coding: utf-8 -*-
"""全镜像扫实体中段 +0x12..+0x1f 的读写点, 重点 +0x1c / +0x1d / +0x1f。"""
import re, struct
from collections import Counter, defaultdict
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
mem = open(MEM, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

GEN = {"eax", "ecx", "edx", "ebx", "esi", "edi"}
TARGETS = {0x1C, 0x1D, 0x1F}
NEIGH = set(range(0x12, 0x20))

INS = []
o = 0
while o < len(mem) - 1:
    last = None
    for ins in md.disasm(mem[o:o + 4096], BASE + o):
        last = ins.address - BASE + ins.size
        INS.append((ins.address, ins.mnemonic, ins.op_str, ins.size))
    o = last if last and last > o else o + 4096
print(f"收集指令 {len(INS)} 条")

pat = re.compile(r"(byte|word|dword) ptr \[(\w+)(?: \+ (0x[0-9a-f]+|\d+))?\]")

hits = defaultdict(lambda: defaultdict(list))
for addr, mn, ops, sz in INS:
    if mn not in ("mov", "movzx", "movsx", "add", "sub", "or", "and", "xor",
                  "inc", "dec", "cmp", "test", "shl", "shr", "lea"):
        continue
    for m in pat.finditer(ops):
        width, reg, d = m.group(1), m.group(2), m.group(3)
        if reg not in GEN or not d:
            continue
        dv = int(d, 0)
        if dv not in NEIGH:
            continue
        is_write = False
        # 写: mov [..], reg/imm  或 add/or/and/xor/inc/dec [..], ..
        if "," in ops:
            dst = ops.split(",")[0].strip()
            if re.match(rf"(byte|word|dword) ptr \[\w+ \+ {re.escape(d)}\]", dst):
                is_write = mn in ("mov", "add", "sub", "or", "and", "xor", "inc", "dec",
                                  "shl", "shr")
        hits[dv]["W" if is_write else "R"].append((addr, mn, ops))

print("\n" + "=" * 84)
print("A. 实体中段 +0x12..+0x1f 读写点计数")
print("=" * 84)
print(f"  {'偏移':<8}{'读':>6}{'写':>6}   备注")
NOTE = {0x1B: "生年(续131)", 0x1C: "← BSDATA @40", 0x1D: "← BSDATA @41",
        0x1E: "← BSDATA @42", 0x1F: "← BSDATA @43"}
for dv in sorted(NEIGH):
    r, w = len(hits[dv]["R"]), len(hits[dv]["W"])
    print(f"  +{dv:#04x}  {r:>6}{w:>6}   {NOTE.get(dv, '')}")

# 函数起点
starts = set()
for i in range(len(mem) - 5):
    if mem[i] == 0xE8:
        rel = struct.unpack_from("<i", mem, i + 1)[0]
        starts.add((BASE + i + 5 + rel) & 0xFFFFFFFF)
starts = sorted(starts)


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


print("\n" + "=" * 84)
print("B. +0x1c / +0x1d / +0x1f 的写入点（含所在函数）")
print("=" * 84)
for dv in TARGETS:
    ws = hits[dv]["W"]
    print(f"\n  === +{dv:#04x}  写入 {len(ws)} 处 ===")
    fns = Counter()
    for a, mn, ops in ws:
        fns[owner(a)] += 1
    for f, n in fns.most_common(8):
        print(f"    函数 {f:#010x} x{n}")
    for a, mn, ops in ws[:10]:
        print(f"      {a:08x}  {mn:<6} {ops}")

print("\n" + "=" * 84)
print("C. +0x1c / +0x1d / +0x1f 的读取点（前 12 条）")
print("=" * 84)
for dv in TARGETS:
    rs = hits[dv]["R"]
    print(f"\n  === +{dv:#04x}  读取 {len(rs)} 处 ===")
    for a, mn, ops in rs[:12]:
        print(f"      {a:08x}  {mn:<6} {ops}")

print("\n" + "=" * 84)
print("D. 函数起点候选: 是否存在 setter 家族写 +0x12..+0x1f")
print("=" * 84)
# 找 0x49xxxx 段内写 [ecx+d] 的短函数
cand = defaultdict(list)
for dv in sorted(NEIGH):
    for a, mn, ops in hits[dv]["W"]:
        cand[owner(a)].append((dv, a, mn, ops))
for f in sorted(k for k in cand if k and 0x498000 <= k < 0x49C000):
    items = cand[f]
    print(f"  {f:#010x}: " + ", ".join(f"+{d:#04x}" for d, *_ in items))
