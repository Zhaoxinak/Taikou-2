# -*- coding: utf-8 -*-
"""定位真正的 BSDATA 59B 读取器 + 实体初始化 0x409340 的字段搬运。"""
import struct, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
mem = open(MEM_PATH, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

TARGETS = {
    "bsd_reader_49": 0x47D890,
}


def e8_callers(target):
    hits = []
    for i in range(len(mem) - 5):
        if mem[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", mem, i + 1)[0]
        dst = (BASE + i + 5 + rel) & 0xFFFFFFFF
        if dst == target:
            hits.append(BASE + i)
    return hits


def ctx(addr, back=16, fwd=6):
    o = addr - BASE
    start = max(0, o - 140)
    seq = []
    for ins in md.disasm(mem[start:o + 40], BASE + start):
        seq.append((ins.address, ins.mnemonic, ins.op_str, ins.size))
    idx = next((k for k, s in enumerate(seq) if s[0] == addr), None)
    if idx is None:
        return seq[-back:]
    return seq[max(0, idx - back):idx + fwd]


print("=" * 78)
print("A. 读助手 0x4411b0 的全部 e8 调用方 (看 size 立即数)")
print("=" * 78)
callers = e8_callers(0x4411B0)
print(f"共 {len(callers)} 处\n")
sizes = {}
for a in callers:
    seq = ctx(a, 10, 2)
    pre = " | ".join(f"{m} {o}" for ad, m, o, s in seq if ad < a)
    # 找 call 前的 push imm
    imms = re.findall(r"push\s+(0x[0-9a-f]+)", pre)
    key = tuple(imms[-2:]) if imms else ()
    sizes.setdefault(key, []).append(a)
for k, v in sorted(sizes.items(), key=lambda x: -len(x[1])):
    print(f"  push 立即数 {str(k):<24} x{len(v):<4} 例: {[hex(x) for x in v[:4]]}")

print("\n" + "=" * 78)
print("B. 全镜像扫 59(0x3b) 与 49(0x31) 作为读取 size 的 push，找含乘法的站点")
print("=" * 78)
# 找 push 0x3b 且上下文含 lea [reg+reg*N] 或 imul
hits59 = [m.start() for m in re.finditer(rb"\x6a\x3b", mem)]      # push 0x3b
hits59 += [m.start() for m in re.finditer(rb"\x68\x3b\x00\x00\x00", mem)]  # push 0x3b (imm32)
print(f"push 0x3b 站点: {len(hits59)}")
for h in hits59[:40]:
    va = BASE + h
    seq = ctx(va, 8, 2)
    txt = " ; ".join(f"{m} {o}" for ad, m, o, s in seq)
    if "imul" in txt or "lea" in txt or "shl" in txt:
        print(f"  0x{va:08x}: {txt[:150]}")

print("\n" + "=" * 78)
print("C. 实体初始化 0x409340 (BSDATA -> 实体 字段搬运?)")
print("=" * 78)
o = 0x409340 - BASE
n = 0
for ins in md.disasm(mem[o:o + 3000], 0x409340):
    print(f"  {ins.address:08x}  {ins.mnemonic:<8} {ins.op_str}")
    n += 1
    if ins.mnemonic == "ret" or n > 130:
        break
