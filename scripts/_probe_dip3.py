# -*- coding: utf-8 -*-
"""
_probe_dip3.py —
  A) 解码 0x4c5b70 工作结果跳表（16 项）
  B) 查 MSGX 文本：0x875, 0x89e..0x8a4
  C) 精确计算 0x525ea0 的 (ptr-0x51eb88) 除数
  D) 反汇编 0x4c5de0 / 0x4c5ef0 / 0x4c4300
"""
import json, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
MEM = open(MEM_PATH, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def rd(va, n):
    o = va - BASE
    return MEM[o:o + n]


def dword(va):
    return struct.unpack("<I", rd(va, 4))[0]


def dis(va, maxins=120):
    o = va - BASE
    out = []
    for ins in md.disasm(MEM[o:o + maxins * 8], va):
        out.append(f"  {ins.address:#x}  {ins.mnemonic:<8} {ins.op_str}")
        if len(out) >= maxins or ins.mnemonic == "ret":
            break
    return "\n".join(out)


print("=" * 78)
print("### A) 工作结果跳表 0x4c5b70 —— 16 项")
print("=" * 78)
WORK = ['高压外交', '友好外交', '谋略', '卖出军粮', '购入军粮', '购入军马',
        '购入洋枪', '开垦农田', '训练', '修复', '筑城', '朝廷工作',
        '收集情报', '移动居城', '武者修行', '茶会']
for i in range(16):
    t = dword(0x4C5B70 + i * 4)
    print(f"  [{i:2}] {WORK[i]:<6} -> {t:#x}")

print()
print("=" * 78)
print("### B) MSGX 文本 (file = id//2000, slot = id%2000)")
print("=" * 78)
d = json.load(open("F:/Games/Taikou 2/scripts/msgx_all_texts.json", encoding="utf-8"))
texts = d["texts"]
ids = [0x875] + list(range(0x89E, 0x8B0))
for gid in ids:
    for k in (str(gid), gid):
        if k in texts:
            print(f"  {gid:#6x} (={gid:5d}) file{gid//2000+1}#{gid%2000:<4} : {texts[k]}")
            break
    else:
        print(f"  {gid:#6x} (={gid:5d}) : <NOT FOUND>")

print()
print("=" * 78)
print("### C) 0x525ea0 除数推算  magic=0x84210843, sar 4, base=0x51eb88")
print("=" * 78)
M = 0x84210843
for dv in range(2, 200):
    # signed-magic 形式: (M * x) >> 32, add x, sar 4
    # 近似 divisor = 2^(32+4) / (M + 2^32)  ... 用实测代替
    pass
# 实测: 取 x = dv*k, 反推
def f(x):
    e = (M * x) & 0xFFFFFFFF
    hi = (M * x) >> 32
    # imul 有符号: 先按有符号算
    sx = x - (1 << 32) if x >= (1 << 31) else x
    prod = M * sx
    hi = (prod >> 32) & 0xFFFFFFFF
    # add edx, ecx (ecx = sx)
    v = hi + sx
    # sar 4 (算术右移, 32位)
    v = v & 0xFFFFFFFF
    if v & 0x80000000:
        v -= (1 << 32)
    return v >> 4

for dv in range(2, 300):
    ok = all(f(dv * k) == k for k in range(1, 60))
    if ok:
        print(f"  divisor = {dv}   (验证 k=1..59 全对)")
        break
else:
    print("  未找到精确除数; 抽样: ", [(k, f(k)) for k in (10, 20, 31, 40, 47, 62)])

print()
for label, va in [("D1) 0x4c4300 选单/选择器", 0x4C4300),
                  ("D2) 0x4c5de0", 0x4C5DE0),
                  ("D3) 0x4c5ef0", 0x4C5EF0)]:
    print("=" * 78)
    print("### " + label)
    print("=" * 78)
    print(dis(va, 130))
    print()
