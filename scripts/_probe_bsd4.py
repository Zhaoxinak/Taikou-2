# -*- coding: utf-8 -*-
"""① BSDATA 是否 XOR 编码  ② 全镜像技能位域访问器扫描 (+0xf/+0x10/+0x11)。"""
import struct, re
from collections import Counter
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BSD = "F:/Games/Taikou 2/Taikou2 Original/BSDATA1.TR2"
BSD2 = "F:/Games/Taikou 2/Taikou2 Original/BSDATA2.TR2"
BASE = 0x400000
mem = open(MEM_PATH, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

print("=" * 78)
print("A. BSDATA1.TR2 头 64 字节 + 是否 XOR 可解")
print("=" * 78)
b = open(BSD, "rb").read()
print(f"size={len(b)}  = 59*700? {len(b) == 59 * 700}")
print("头 64B:", " ".join(f"{x:02x}" for x in b[:64]))
print("作 GBK 试解:", b[:16].decode("gbk", "replace"))
# 记录 1 (idx=1) 偏移 59..118
print("\nidx=1 (off 59) 头 32B:", " ".join(f"{x:02x}" for x in b[59:91]))
print("  作 GBK:", b[59:75].decode("gbk", "replace"))

# 检测 XOR key: 用已知的 padding 位置 (@13=00,@14=FF,@15=FF,@18=FF,@19=FF,@30=FF,@32..38=00)
# 若明文, 则 b[59*i+13]==0 等。统计
print("\n--- padding 位一致性 (明文假设) ---")
pads = {13: 0x00, 14: 0xFF, 15: 0xFF, 18: 0xFF, 19: 0xFF, 30: 0xFF}
for off, exp in pads.items():
    vals = [b[59 * i + off] for i in range(700)]
    c = Counter(vals).most_common(3)
    ok = sum(1 for v in vals if v == exp)
    print(f"  @{off:>2} 期望 {exp:#04x}: 匹配 {ok}/700  实际 top3={[(hex(k), n) for k, n in c]}")

print("\n--- 若 XOR: 用 @13 应为 0 反推 key ---")
ks = Counter(b[59 * i + 13] for i in range(700))
print(f"  @13 实际值分布 top5: {[(hex(k), n) for k, n in ks.most_common(5)]}")
ks14 = Counter(b[59 * i + 14] for i in range(700))
print(f"  @14 实际值分布 top5: {[(hex(k), n) for k, n in ks14.most_common(5)]}")

print("\n" + "=" * 78)
print("B. 全镜像: 对 byte[reg+0xf] / [reg+0x10] / [reg+0x11] 的位掩码访问")
print("=" * 78)
GEN = {"eax", "ecx", "edx", "ebx", "esi", "edi"}
MASKN = {0x3: "bits0-1", 0xC: "bits2-3", 0x30: "bits4-5", 0xC0: "bits6-7"}
# 线性反汇编全镜像代码区, 找 movzx/mov 取 byte[reg+D] 之后紧跟 and reg, mask
found = Counter()
detail = []
for ins in md.disasm(mem, BASE):
    if ins.mnemonic not in ("mov", "movzx"):
        continue
    ops = ins.op_str
    if not ops or "," not in ops:
        continue
    dst, src = ops.split(",", 1)
    src = src.strip()
    m = re.match(r"byte ptr \[(\w+)(?: \+ (0x[0-9a-f]+))?\]$", src)
    if not m:
        continue
    reg, d = m.group(1), m.group(2)
    if reg not in GEN:
        continue
    dv = int(d, 16) if d else 0
    if dv not in (0xF, 0x10, 0x11):
        continue
    # 看下一条是否 and
    nxt = None
    try:
        nxt = next(md.disasm(mem[ins.address - BASE + ins.size: ins.address - BASE + ins.size + 12],
                             ins.address + ins.size))
    except StopIteration:
        pass
    if nxt is None or nxt.mnemonic != "and":
        continue
    mm = re.match(r"(\w+), (0x[0-9a-f]+)$", nxt.op_str)
    if not mm:
        continue
    mask = int(mm.group(2), 16)
    key = (dv, mask)
    found[key] += 1
    detail.append((ins.address, dv, mask, ins.op_str, nxt.op_str))

print(f"  {'字段':<10}{'掩码':<10}{'位':<10}次数")
for (dv, mask), n in sorted(found.items()):
    print(f"  +0x{dv:<8x}{hex(mask):<10}{MASKN.get(mask, '?'):<10}{n}")

print("\n  --- 样例 (每 (字段,掩码) 前 3 条) ---")
seen = Counter()
for addr, dv, mask, o1, o2 in detail:
    k = (dv, mask)
    if seen[k] >= 3:
        continue
    seen[k] += 1
    print(f"    {addr:08x}  {o1:<34} ; {o2}")
