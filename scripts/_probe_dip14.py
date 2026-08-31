# -*- coding: utf-8 -*-
"""
_probe_dip14.py —
  A) 找 0x4b94xx 结算函数的真正入口 + 跳表
  B) 查 msg 0x92a/0x92e/0x92f..0x935 文本
  C) 反汇编 0x4d9e50 (目标国属性) / 0x4b9c10
"""
import json, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
MEM = open(MEM_PATH, "rb").read()
SZ = len(MEM)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def dword(va):
    o = va - BASE
    return struct.unpack("<I", MEM[o:o + 4])[0]


def dis(va, maxins=120):
    o = va - BASE
    out = []
    for ins in md.disasm(MEM[o:o + maxins * 8], va):
        out.append(f"  {ins.address:#x}  {ins.mnemonic:<8} {ins.op_str}")
        if len(out) >= maxins or ins.mnemonic == "ret":
            break
    return "\n".join(out)


print("=" * 78)
print("### A) 0x4b8f00..0x4b94b0 反汇编（找入口与跳表）")
print("=" * 78)
print(dis(0x4B8F00, 0))  # placeholder
o = 0x4B8F00 - BASE
for ins in md.disasm(MEM[o:o + 0x600], 0x4B8F00):
    print(f"  {ins.address:#x}  {ins.mnemonic:<8} {ins.op_str}")
    if ins.address >= 0x4B94AC:
        break

print()
print("=" * 78)
print("### A2) 扫描 0x4b9000..0x4b94ac 中的 dword 跳表项")
print("=" * 78)
start = 0x4B9000 - BASE
end = 0x4B94AC - BASE
run = []
for i in range(start, end - 4, 4):
    v = struct.unpack("<I", MEM[i:i + 4])[0]
    if 0x4B94A0 <= v <= 0x4B9C00:
        run.append((BASE + i, v))
if run:
    # 连续段
    seg = [run[0]]
    for x in run[1:]:
        if x[0] - seg[-1][0] == 4:
            seg.append(x)
        else:
            print(f"  --- 表段 {seg[0][0]:#x} ({len(seg)} 项) ---")
            for a, v in seg:
                print(f"    {a:#x} -> {v:#x}")
            seg = [x]
    print(f"  --- 表段 {seg[0][0]:#x} ({len(seg)} 项) ---")
    for a, v in seg:
        print(f"    {a:#x} -> {v:#x}")
else:
    print("  (未找到)")

print()
print("=" * 78)
print("### B) 相关消息文本")
print("=" * 78)
d = json.load(open("F:/Games/Taikou 2/scripts/msgx_all_texts.json", encoding="utf-8"))
T = {}
for k, v in d["texts"].items():
    try:
        T[int(k)] = v
    except Exception:
        pass
for gid in list(range(0x928, 0x938)) + [0x92A, 0x92E]:
    gid = gid & 0xFFFFFF
    print(f"  {gid:#6x} ({gid:5d}): {T.get(gid, '<none>')}")

print()
print("=" * 78)
print("### C) 0x4d9e50 —— 目标国属性")
print("=" * 78)
print(dis(0x4D9E50, 120))
print()
print("### C2) 0x4b9c10")
print(dis(0x4B9C10, 120))
