# -*- coding: utf-8 -*-
"""
_probe_dip15.py — 解码使者归还结算跳表
  A) 映射表 0x4b90d8 (byte[45])
  B) 跳表 0x4b90c4 (dword[N])
  C) 相关消息文本
  D) 各 handler 的开头若干条指令（识别语义）
"""
import json, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
MEM = open(MEM_PATH, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

MAP = 0x4B90D8
NMAP = 45
JT = 0x4B90C4


def bytemap():
    o = MAP - BASE
    return list(MEM[o:o + NMAP])


m = bytemap()
print("=" * 78)
print("### A) 次级映射表 0x4b90d8 (byte[45], 索引 = 工作类型-2)")
print("=" * 78)
for i, v in enumerate(m):
    print(f"  work={i+2:<3} -> handler_idx {v}")
mx = max(m)
print(f"\n  max handler_idx = {mx}  => 跳表至少 {mx+1} 项")

print()
print("=" * 78)
print(f"### B) 跳表 0x4b90c4 ({mx+1} 项)")
print("=" * 78)
jt = []
for i in range(mx + 1):
    o = JT - BASE + i * 4
    v = struct.unpack("<I", MEM[o:o + 4])[0]
    jt.append(v)
    print(f"  [{i:2}] {JT + i*4:#x} -> {v:#x}")

print()
print("=" * 78)
print("### A+B) 工作类型 -> handler 全映射")
print("=" * 78)
idx2h = {}
for i, v in enumerate(m):
    idx2h.setdefault(i + 2, jt[v])
for w in sorted(idx2h):
    print(f"  work {w:<3} -> {idx2h[w]:#x}")

print()
print("=" * 78)
print("### C) 消息文本 0x8ff..0x935")
print("=" * 78)
d = json.load(open("F:/Games/Taikou 2/scripts/msgx_all_texts.json", encoding="utf-8"))
T = {}
for k, v in d["texts"].items():
    try:
        T[int(k)] = v
    except Exception:
        pass
for gid in list(range(0x8FF, 0x938)):
    print(f"  {gid:#6x} ({gid:5d}): {T.get(gid, '<none>')}")

print()
print("=" * 78)
print("### D) 前若干个 handler 的开头（识别语义）")
print("=" * 78)
for h in sorted(set(idx2h.values()))[:14]:
    o = h - BASE
    print(f"\n--- {h:#x} ---")
    n = 0
    for ins in md.disasm(MEM[o:o + 0x90], h):
        print(f"  {ins.address:#x}  {ins.mnemonic:<8} {ins.op_str}")
        n += 1
        if n >= 16:
            break
