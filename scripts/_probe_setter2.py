# -*- coding: utf-8 -*-
"""用全镜像 call 目标定出 0x49a300..0x49a5c0 区间的真实函数入口, 逐条反汇编。"""
import re, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
mem = open(MEM, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

LO, HI = 0x49A300, 0x49A5C0

# 全镜像 e8 目标
targets = {}
for i in range(len(mem) - 5):
    if mem[i] != 0xE8:
        continue
    rel = struct.unpack_from("<i", mem, i + 1)[0]
    dst = (BASE + i + 5 + rel) & 0xFFFFFFFF
    if LO <= dst < HI:
        targets.setdefault(dst, []).append(BASE + i)

print("=" * 80)
print(f"A. 区间 [{LO:#x},{HI:#x}) 内被 e8 调用的地址 (真实入口)")
print("=" * 80)
print(f"  共 {len(targets)} 个入口\n")
for t in sorted(targets):
    o = t - BASE
    body = []
    for ins in md.disasm(mem[o:o + 60], t):
        body.append((ins.address, ins.mnemonic, ins.op_str))
        if ins.mnemonic == "ret":
            break
    txt = " | ".join(f"{m} {p}" for _, m, p in body)
    m1 = re.search(r"byte ptr \[ecx \+ (0x[0-9a-f]+|\d+)\]", txt)
    m2 = re.search(r"and al, (0x[0-9a-f]+|\d+)", txt)
    m3 = re.search(r"shl al, (0x[0-9a-f]+|\d+)", txt)
    bits = {0xFC: 0, 0xF3: 2, 0xCF: 4, 0x3F: 6}
    if m1 and m2:
        by = int(m1.group(1), 0)
        mask = int(m2.group(1), 0)
        sh = int(m3.group(1), 0) if m3 else 0
        b = bits.get(mask, "?")
        print(f"  {t:08x}  callers={len(targets[t]):<3} byte[ecx+{by:#04x}] "
              f"mask={mask:#04x} bit={b} shl={sh}")
    else:
        print(f"  {t:08x}  callers={len(targets[t]):<3} (非 2-bit setter) "
              f"{txt[:70]}")

print("\n" + "=" * 80)
print("B. 全部调用点 (去重) 及其上下文: 对象基址 + 传入的字段值来源")
print("=" * 80)
allsites = sorted({x for v in targets.values() for x in v})
print(f"  去重调用点 {len(allsites)} 处\n")


def ctx(addr, back=10):
    o = addr - BASE
    st = max(0, o - 90)
    seq = []
    for ins in md.disasm(mem[st:o + 8], BASE + st):
        seq.append((ins.address, ins.mnemonic, ins.op_str))
    idx = next((k for k, s in enumerate(seq) if s[0] == addr), None)
    return seq[max(0, (idx or 0) - back): (idx or 0) + 2]


seen_ctx = []
for a in allsites:
    c = ctx(a)
    key = tuple((m, p) for _, m, p in c[-4:])
    if key in seen_ctx:
        continue
    seen_ctx.append(key)
    print(f"  --- call @ {a:08x} ---")
    for ad, m, p in c:
        mark = " <<<" if ad == a else ""
        print(f"    {ad:08x}  {m:<8} {p}{mark}")
    print()

print("=" * 80)
print("C. 全局 0x513b14 / 0x513aff..0x513b01 的引用统计")
print("=" * 80)
for g in (0x513B14, 0x513AFF, 0x513B00, 0x513B01, 0x513B02):
    pat = struct.pack("<I", g)
    hits = [m.start() for m in re.finditer(re.escape(pat), mem)]
    print(f"  {g:#010x}: {len(hits)} 处  {[hex(BASE + h) for h in hits[:8]]}")
