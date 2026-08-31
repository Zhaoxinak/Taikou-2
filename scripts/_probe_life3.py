# -*- coding: utf-8 -*-
"""以 1490(0x5D2) 为锚反查: 全镜像搜该立即数的所有出现处。"""
import re, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
mem = open(MEM, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

CANDS = {
    "1490 (0x5d2)": (1490, "0x5d2"),
    "1491": (1491, "0x5d3"),
    "1550": (1550, "0x60e"),   # 已知: 0x5205f0 = 年偏移 +1560 (0x618)
    "1560": (1560, "0x618"),
    "1600": (1600, "0x640"),
    "1500": (1500, "0x5dc"),
}

print("=" * 78)
print("A. 全镜像搜 4 字节小端立即数 1490 / 1491 / 1500 / 1550 / 1560 / 1600")
print("=" * 78)
for label, (val, hx) in CANDS.items():
    pat = struct.pack("<I", val)
    hits = [m.start() for m in re.finditer(re.escape(pat), mem)]
    print(f"\n  {label:<14} {hx:<7} 字节序列 {pat.hex()} 命中 {len(hits)} 处")
    for h in hits[:14]:
        va = BASE + h
        # 反汇编该处附近
        o = max(0, h - 10)
        seq = []
        for ins in md.disasm(mem[o:h + 12], BASE + o):
            seq.append((ins.address, ins.mnemonic, ins.op_str))
            if len(seq) > 6:
                break
        txt = " ; ".join(f"{m} {p}" for _, m, p in seq)
        print(f"    {va:08x}: {txt[:120]}")

print("\n" + "=" * 78)
print("B. 搜 16 位形式 0x05d2 (68 d2 05 / 66 b8 d2 05 / b8 d2 05 00 00)")
print("=" * 78)
for pat, lbl in ((b"\x68\xd2\x05\x00\x00", "push 0x5d2"),
                 (b"\xb8\xd2\x05\x00\x00", "mov eax,0x5d2"),
                 (b"\x05\xd2\x05\x00\x00", "add eax,0x5d2"),
                 (b"\x6a\xd2", "push 0xd2 (byte)")):
    hits = [m.start() for m in re.finditer(re.escape(pat), mem)]
    print(f"  {lbl:<18} x{len(hits)}  {[hex(BASE + h) for h in hits[:10]]}")

print("\n" + "=" * 78)
print("C. 全镜像搜 and r8/r32, 0x7f (0x7f 掩码) 且附近有 0x5d2/0x5d3")
print("=" * 78)
# and r32,0x7f : 83 E0 7F (eax) / 83 E1 7F (ecx) / 83 E2 7F / 83 E3 7F / 83 E6 7F / 83 E7 7F
regs = {0xE0: "eax", 0xE1: "ecx", 0xE2: "edx", 0xE3: "ebx", 0xE6: "esi", 0xE7: "edi"}
cnt = 0
for modrm, rn in regs.items():
    pat = bytes([0x83, modrm, 0x7F])
    for m in re.finditer(re.escape(pat), mem):
        va = BASE + m.start()
        # 前后 64 字节内是否出现 d2 05 或 d3 05
        lo, hi = max(0, m.start() - 64), m.start() + 64
        win = mem[lo:hi]
        if b"\xd2\x05" in win or b"\xd3\x05" in win:
            o = max(0, m.start() - 24)
            seq = []
            for ins in md.disasm(mem[o:m.start() + 24], BASE + o):
                seq.append((ins.address, ins.mnemonic, ins.op_str))
                if len(seq) > 8:
                    break
            print(f"    {va:08x}: " + " ; ".join(f"{a} {p}" for a, _, p in seq))
            cnt += 1
            if cnt > 20:
                break
    if cnt > 20:
        break
print(f"  (共列出 {cnt} 条)")

print("\n" + "=" * 78)
print("D. 验证: @39&0x7f 反推生年 vs 史実 (扩大样本, 用旧历年)")
print("=" * 78)
B1 = "F:/Games/Taikou 2/Taikou2 Original/BSDATA1.TR2"
b1 = open(B1, "rb").read()
REC, N = 59, 700


def nm(i):
    o = REC * i
    return (b1[o:o + 7].split(b"\x00")[0].decode("gbk", "replace") +
            b1[o + 7:o + 13].split(b"\x00")[0].decode("gbk", "replace"))


idx = {nm(i): i for i in range(N)}
KNOWN = [
    ("织田信长", 1534), ("武田信玄", 1521), ("上杉谦信", 1530), ("德川家康", 1542),
    ("毛利元就", 1497), ("今川义元", 1519), ("斋藤道三", 1494), ("明智光秀", 1528),
    ("服部半藏", 1542), ("伊达政宗", 1567), ("真田幸村", 1567), ("石田三成", 1560),
    ("柴田胜家", 1521), ("丹羽长秀", 1535), ("前田利家", 1538), ("蜂须贺小六", 1526),
    ("今川氏真", 1538), ("武田胜赖", 1546), ("北条氏政", 1538), ("上杉景胜", 1555),
    ("黑田官兵卫", 1546), ("竹中半兵卫", 1544), ("浅井长政", 1545),
]
bad = 0
for n_, by in KNOWN:
    i = idx.get(n_)
    if i is None:
        continue
    v = b1[REC * i + 39] & 0x7F
    pred = 1490 + v
    flag = "OK " if pred == by else "DIFF"
    if pred != by:
        bad += 1
    print(f"  {flag} {n_:<12} 史実生年={by}  @39&7f={v:<3} 1490+{v}={pred}")
print(f"\n  不合 {bad}/{len([k for k in KNOWN if k[0] in idx])}")
