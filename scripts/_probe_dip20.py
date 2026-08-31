# -*- coding: utf-8 -*-
"""
_probe_dip20.py — 收尾校验
  A) 魔数 0x66666667 (sar 3) 的真实除数
  B) 0x4b97a8 共通尾（功勋/报酬）
  C) 0x4b94ac(友好外交) / 0x4b94f4(高压外交) 精读
"""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
MEM = open(MEM_PATH, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def s32(v):
    return v - (1 << 32) if v & 0x80000000 else v


def dis(va, maxb=0x300, maxins=80):
    o = va - BASE
    out = []
    for ins in md.disasm(MEM[o:o + maxb], va):
        out.append(f"  {ins.address:#x}  {ins.mnemonic:<8} {ins.op_str}")
        if len(out) >= maxins or ins.mnemonic == "ret":
            break
    return "\n".join(out)


print("=" * 78)
print("### A) 魔数 0x66666667 (imul; sar 3) 的除数")
print("=" * 78)
M = s32(0x66666667)


def f(x):
    prod = M * x
    hi = (prod >> 32) & 0xFFFFFFFF
    hi = s32(hi)
    v = hi >> 3
    # 符号修正: mov ecx,edx; shr ecx,0x1f; add edx,ecx
    sg = (v >> 31) & 1 if False else 0
    return v


tests = [0, 5, 9, 10, 19, 20, 25, 30, 39, 40, 50, 59, 60, 79, 80, 99, 100]
print("  r -> f(r):", {r: f(r) for r in tests})
for dv in range(2, 130):
    if all(f(dv * k) == k for k in range(1, 40)):
        print(f"  ==> divisor = {dv}  (k=1..39 全对)")
        break
else:
    print("  未精确匹配")

print()
print("=" * 78)
print("### C1) 0x4b94ac 友好外交(work 9) 精读")
print("=" * 78)
print(dis(0x4B94AC, 0x60, 30))

print()
print("### C2) 0x4b94f4 高压外交(work 10) 精读")
print("=" * 78)
print(dis(0x4B94F4, 0x60, 30))

print()
print("=" * 78)
print("### B) 0x4b97a8 共通尾")
print("=" * 78)
print(dis(0x4B97A8, 0x220, 80))
