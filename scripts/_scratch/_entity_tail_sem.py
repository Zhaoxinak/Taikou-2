# -*- coding: utf-8 -*-
"""Entity-specific analysis for +0x1c/+0x1f/+0x20 and relation field."""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
import struct, os
from collections import Counter

BASE = 0x400000
mem = open("scripts/_unpacked_mem.bin", "rb").read()
bs = open("Taikou2 Original/BSDATA1.TR2", "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
STRIDE, N, ENT = 59, 700, 47
ENT_BASE = 0x519868

def show(va, n=0x100, label=""):
    print(f"\n==== {va:#x} {label} ====")
    for ins in md.disasm(mem[va - BASE:va - BASE + n], va):
        print(f"  {ins.address:#x}: {ins.mnemonic:8} {ins.op_str}")
        if ins.mnemonic.startswith("ret") and ins.address > va + 0x20:
            break

# 1) Loader: find where BSDATA byte is written to entity+0x1c
# Search for pattern near 0x47df76 (known remap)
show(0x47df00, 0x120, "loader around remap")
show(0x47de00, 0x50, "loader start")

# 2) Entity consumers: search for ×47 sequences near +0x1c/+0x1f reads
# lea r,[r+r*2]; shl r,4; sub r,r = ×47
print("\n==== scan code for entity×47 then nearby +0x1c/1f/20 ====")
# simpler: find movzx/mov from [reg+0x1c] where recent code has 0x519868
needle = struct.pack("<I", ENT_BASE)
idxs = []
start = 0
while True:
    i = mem.find(needle, start)
    if i < 0 or i > 0xF0000:
        break
    idxs.append(BASE + i)
    start = i + 1
print(f"refs to 0x519868: {len(idxs)}")

# For each ref, disasm a window and see if +0x1c..+0x20 accessed
interesting = []
for va in idxs:
    # window -0x20 .. +0x80 around the immediate use
    # find instruction containing this immediate
    window_start = va - 0x40
    code = mem[window_start - BASE: window_start - BASE + 0xC0]
    text_hits = []
    for ins in md.disasm(code, window_start):
        for d in (0x1c, 0x1d, 0x1e, 0x1f, 0x20):
            if f"+ {d:#x}" in ins.op_str:
                text_hits.append((ins.address, ins.mnemonic, ins.op_str, d))
    if text_hits:
        interesting.append((va, text_hits))

print(f"entity-base refs with +0x1c..20 nearby: {len(interesting)}")
for va, hits in interesting[:40]:
    print(f"\n  imm@{va:#x}:")
    for a, m, o, d in hits:
        print(f"    {a:#x}: {m} {o}")

# 3) Stamina UI text cross: MSGX id1 = 体力说明
show(0x4453a0, 0x80, "stamina recover gap formula")
show(0x452fa0, 0x60, "read +0x20")
show(0x44d4e0, 0x80, "read +0x20 sites")
show(0x410dc0, 0x60, "read +0x1c")
show(0x447970, 0x80, "read +0x1c")
show(0x46b2e0, 0x80, "copy +0x20?")

# 4) Relation type samples with names to UTF-8 file
def name(i):
    r = bs[i * STRIDE:(i + 1) * STRIDE]
    s = r[0:7].split(b"\x00")[0].decode("gbk", "replace")
    g = r[7:14].split(b"\x00")[0].decode("gbk", "replace")
    return s + g

print("\n==== relation type samples ====")
for typ in (0, 1, 2):
    print(f"\n-- type {typ} --")
    n = 0
    for i in range(N):
        r = bs[i * STRIDE:(i + 1) * STRIDE]
        if r[0x2a] != typ:
            continue
        d = r[0x29]
        if d == 0xFF or d >= N:
            continue
        print(f"  {name(i)} -> {name(d)} (id {d})")
        n += 1
        if n >= 12:
            break

# 5) +0x1c bit analysis vs known flags
print("\n==== +0x1c value structure ====")
vals = [bs[i * STRIDE + 0x28] for i in range(N) if not name(i).startswith("姓")]
# decompose
for bit in range(8):
    c = sum(1 for v in vals if v & (1 << bit))
    print(f"  bit{bit}: {c}/{len(vals)}")
# high bits as level: v>>5
print("top v>>5:", Counter(v >> 5 for v in vals).most_common())
print("top v&0x1f:", Counter(v & 0x1F for v in vals).most_common(10))
print("top v&~0x3c (clear flag bits 2-5):", Counter(v & ~0x3C for v in vals).most_common(10))

# 6) +0x1f — compare to face / birth month / something in known tables
print("\n==== +0x1f analysis ====")
v1f = [bs[i * STRIDE + 0x2b] for i in range(N) if not name(i).startswith("姓")]
print("unique", len(set(v1f)), "range", min(v1f), max(v1f))
# birth year low correlation?
by = [bs[i * STRIDE + 0x27] & 0x7F for i in range(N) if not name(i).startswith("姓")]
# group average birth by 1f
from statistics import mean
groups = {}
for a, b in zip(v1f, by):
    groups.setdefault(a, []).append(b)
# print a few
print("sample 1f -> avg birth_off, count:")
for k in sorted(groups)[:15]:
    print(f"  {k}: avg={mean(groups[k]):.1f} n={len(groups[k])}")
