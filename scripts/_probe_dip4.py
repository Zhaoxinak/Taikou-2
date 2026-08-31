# -*- coding: utf-8 -*-
"""
_probe_dip4.py — 直击「关系值」本体
  A) 反汇编 0x49fe70 —— 0x4c4270 里 (clan, province) -> ax 的关系取值函数
  B) 全映像扫描对 0x5179b8 (国政治表) 的【写】操作，按偏移归类
  C) dump 0x5080cc 附近字节（续89 称"8级国关系表无xref"之谜）
  D) 反汇编 0x4c5acd 尾巴 + 0x4c5ad4
"""
import struct, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
MEM = open(MEM_PATH, "rb").read()
SZ = len(MEM)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def rd(va, n):
    o = va - BASE
    return MEM[o:o + n] if 0 <= o else b""


def dis(va, maxins=140):
    o = va - BASE
    out = []
    for ins in md.disasm(MEM[o:o + maxins * 8], va):
        out.append(f"  {ins.address:#x}  {ins.mnemonic:<8} {ins.op_str}")
        if len(out) >= maxins or ins.mnemonic == "ret":
            break
    return "\n".join(out)


print("=" * 78)
print("### A) 0x49fe70 —— 关系取值函数 (0x4c4270 中调用, 返回 ax)")
print("=" * 78)
print(dis(0x49FE70, 140))

print()
print("=" * 78)
print("### C) 0x5080cc 附近 128 字节 dump")
print("=" * 78)
b = rd(0x5080CC, 128)
print("  hex:", " ".join(f"{x:02x}" for x in b))
try:
    i = b.index(0)
    txt = b[:i].decode("gbk")
    print("  gbk:", txt)
except Exception as e:
    print("  decode err:", e)
    print("  gbk(all):", b.decode("gbk", "replace"))

print()
print("=" * 78)
print("### B) 对 0x5179b8 的【写】指令扫描 (全映像线性反汇编)")
print("=" * 78)
# 线性扫描整个代码区(0x401000..0x520000)，找 op_str 含 0x5179b8 的指令
CODE_START, CODE_END = 0x401000, 0x520000
pat = re.compile(r"0x5179b8")
hits = []
o = CODE_START - BASE
end = CODE_END - BASE
while o < end:
    got = False
    for ins in md.disasm(MEM[o:o + 16], BASE + o):
        got = True
        if "0x5179b8" in ins.op_str:
            # 判断读/写: 目标在左边即为写
            ops = ins.op_str.split(",", 1)
            is_write = "0x5179b8" in ops[0]
            hits.append((ins.address, ins.mnemonic, ins.op_str, is_write))
        o += ins.size
        if ins.mnemonic in ("ret", "jmp", "hlt", "ud2"):
            o = ins.address + ins.size - BASE
            break
    if not got:
        o += 1
print(f"  命中 {len(hits)} 条；其中写操作 {sum(1 for h in hits if h[3])} 条\n")
for va, mn, ops, w in hits:
    tag = "WRITE" if w else "read "
    print(f"  {tag}  {va:#x}  {mn:<8} {ops}")
