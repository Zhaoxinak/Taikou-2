# -*- coding: utf-8 -*-
"""dump 職位阈值表 0x50bf88（6 条 × 8B：dword rank / word 勲功阈值 / word 俸禄）"""
import struct, os

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()

OUT = []
def emit(s=""):
    OUT.append(s)

TBL = 0x50BF88
emit("=== 職位阈值表 0x%08x ===" % TBL)
emit("原始字节 (0x50bf88..0x50bfc0):")
emit("  " + MEM[TBL - BASE:TBL - BASE + 0x38].hex(" "))
emit("")
emit("%-4s %-10s %-14s %-14s %s" % ("idx", "addr", "dword(rank)", "word(+4)勲功", "word(+6)俸禄"))
RANK = ["浪人", "步兵头", "队长", "侍大将", "部将", "家老", "宿老", "大名", "城主"]
entries = []
for i in range(8):
    off = TBL - BASE + i * 8
    if off + 8 > len(MEM):
        break
    r, m, s = struct.unpack_from("<IHH", MEM, off)
    nm = RANK[r] if r < len(RANK) else "?"
    entries.append((r, m, s))
    emit("  %-2d  0x%08x  %-11d %-14d %-14d  %s" % (i, TBL + i * 8, r, m, s, nm))

emit("")
emit("=== 按 rank 排序的 (勲功阈值, 俸禄) ===")
emit("%-12s %-14s %s" % ("職位", "勲功阈值", "俸禄"))
for (r, m, s) in entries:
    emit("  %-10s %-14d %d" % (RANK[r] if r < len(RANK) else "?", m, s))

# 反查函数 0x49fc60 用的起点
emit("")
emit("0x49fc60 起点 ecx = 0x50bfb0 -> 条目 %d" % ((0x50BFB0 - TBL) // 8))
emit("0x49fc30 扫描条目 0..5 (cmp ax,6)")

# 城表 0x51eb88 的 +0x0a 字段（城主武将编号）抽样
emit("")
emit("=== 城表 0x51eb88 (+0x0a = 城主武将编号) 抽样 ===")
for c in range(8):
    off = 0x51EB88 - BASE + c * 31
    lord = struct.unpack_from("<H", MEM, off + 0x0A)[0]
    emit("  城%d: lord_idx=%d" % (c, lord))

open(os.path.join(HERE, "_table.txt"), "w", encoding="utf-8").write("\n".join(OUT))
print("see _table.txt")
