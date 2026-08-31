#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描实体状态字 word[entity+0x2c] 的 bit15(0x8000) 与 bit7(0x80) 两类「不在」标记
的 setter/clear/tester，按函数聚类并附带调用锚点，用于区分两种语义。
纯静态，不改写任何文件。"""
import os, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()

ANCHOR = {
    0x49a7d0: "set_lord_idx", 0x49a880: "inc_loyalty", 0x49ffc0: "affinity_score",
    0x49c460: "S15_set_a", 0x49c4b0: "S15_set_b", 0x49a990: "castle_rec_copy",
    0x47b900: "display_msg", 0x4ebd60: "RNG", 0x45e3e0: "build_cand_pool",
    0x49f5e0: "get_player", 0x49f830: "get_slot", 0x470690: "is_alive",
    0x47fc60: "sndata_fanout", 0x49b960: "shared_setter_lib", 0x441cc0: "武将選択",
    0x49a750: "copy_prov", 0x4a35e0: "s6_add", 0x49a7e0: "set_status_b8_10",
    0x49f6b0: "get_ctx", 0x49f120: "get_field", 0x4ebcd0: "sat_sub", 0x4ebca0: "sat_add",
}

def dis(va, n):
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.skipdata = True
    off = va - BASE
    return list(md.disasm(bytes(MEM[off:off+n]), va))

def signed_disp(op):
    m = re.search(r'\[([^\]]+)\]', op)
    if not m: return None
    inside = m.group(1)
    adds = re.findall(r'([+\-])\s*(0x[0-9a-f]+|\d+)', inside)
    if not adds: return 0
    val = 0
    for s, h in adds:
        nv = int(h, 16) if h.startswith('0x') else int(h, 10)
        val += nv * (1 if s == '+' else -1)
    return val

# ---- pass1: 收集所有 call 目标作为函数起点 ----
print("线性反汇编全镜像（收集函数边界）...")
all_funcs = set([0x4f44b0, 0x400000])
INS = dis(BASE, len(MEM))
for i in INS:
    if i.mnemonic == "call" and i.op_str.startswith("0x"):
        try: all_funcs.add(int(i.op_str, 16))
        except: pass
all_funcs = sorted(all_funcs)
def func_of(va):
    import bisect
    idx = bisect.bisect_right(all_funcs, va) - 1
    return all_funcs[max(0, idx)]

# ---- pass2: 找 +0x2c 上 bit15/bit7 的 set/clear/test ----
# 直接形态：or/and/test word[..+0x2c], imm  (imm in {0x8000,0x7fff,0x80,0x7f})
# 间接形态：or/and/test ah,0x80 / al,0x80 / ah,0x7f / al,0x7f  (对载入的 word 操作)
DIRECT = {0x8000: ("bit15", "SET"), 0x7fff: ("bit15", "CLR"),
          0x80: ("bit7", "SET"), 0x7f: ("bit7", "CLR")}
INDIRECT = {"ah": {0x80: ("bit15", "SET"), 0x7f: ("bit15", "CLR")},
            "al": {0x80: ("bit7", "SET"), 0x7f: ("bit7", "CLR")}}

hits = []  # (func, addr, bit, op, mnemonic, op_str)
for i in INS:
    m, op = i.mnemonic, i.op_str
    low = op.lower()
    # 直接形态
    if m in ("or", "and", "test") and ("ptr [" in low):
        d = signed_disp(low)
        # 取立即数
        imm_m = re.search(r',\s*(0x[0-9a-f]+|\d+)\s*$', op)
        if d == 0x2c and imm_m:
            imm = int(imm_m.group(1), 16) if imm_m.group(1).startswith('0x') else int(imm_m.group(1), 10)
            if imm in DIRECT:
                bit, kind = DIRECT[imm]
                hits.append((func_of(i.address), i.address, bit, kind, m, op))
    # 间接形态（ah/al 字节操作）
    if m in ("or", "and", "test"):
        mm = re.match(r'(ah|al),\s*(0x[0-9a-f]+|\d+)$', op)
        if mm:
            reg = mm.group(1); imm = int(mm.group(2), 16) if mm.group(2).startswith('0x') else int(mm.group(2), 10)
            if reg in INDIRECT and imm in INDIRECT[reg]:
                bit, kind = INDIRECT[reg][imm]
                hits.append((func_of(i.address), i.address, bit, kind, m, op))

# 去重 + 按函数聚类
from collections import defaultdict
by_func = defaultdict(list)
for h in hits: by_func[h[0]].append(h)

print("命中总数: %d  涉及函数数: %d\n" % (len(hits), len(by_func)))
for fn in sorted(by_func):
    lst = by_func[fn]
    # 取该函数前若干调用锚点
    anchors = set()
    for j in dis(fn, 0x300):
        if j.mnemonic == "call" and j.op_str.startswith("0x"):
            try:
                t = int(j.op_str, 16)
                if t in ANCHOR: anchors.add(ANCHOR[t])
            except: pass
    kinds = sorted(set("%s:%s" % (b, k) for (_, _, b, k, _, _) in lst))
    print("0x%06x  [%s]  %s" % (fn, " ".join(kinds), " ".join(sorted(anchors))))
    for (_, a, b, k, m, op) in sorted(lst):
        print("    0x%x  %-6s %s" % (a, m, op))
