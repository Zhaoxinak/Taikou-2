#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""精修版：只统计对「实体状态字 word[entity+0x2c]」的 bit15(0x8000)/bit7(0x80)
的 SET/CLR（or/and）操作，按函数聚类 + 调用锚点上下文。
通过每函数值流：识别 (a) 直接 [..+0x2c] 内存写；(b) 加载 word[+0x2c] 到某寄存器后
对该寄存器高/低字节做 or/and；(c) 循环基址 esi=0x519868(+0x2c)=>+0x2c / esi=0x519894=>+0x2c。
纯静态，不改写任何文件。"""
import os, re, bisect
from collections import defaultdict
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
    0x4a5571: "継承転封", 0x4a3920: "全員浪人化A", 0x46a4a0: "主君再割当", 0x4a3260: "inc_loyalty2",
    0x452b21: "登用", 0x4a5033: "出奔", 0x4a580e: "転属", 0x4a3eab: "役職解除",
    0x4c3322: "功勲结算", 0x4cb9e0: "相性離反", 0x4e8089: "事件脱离", 0x40ff2c: "浪人生成A",
    0x41004b: "浪人生成B", 0x440e19: "玩家改易", 0x4dd7c0: "S5", 0x49ba30: "S6b2_4",
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

def mem_base_reg(op):
    m = re.search(r'\[([a-z]+)', op)
    return m.group(1) if m else None

# 全镜像 + 函数边界
print("线性反汇编全镜像…")
INS = dis(BASE, len(MEM))
all_funcs = set([0x4f44b0, 0x400000])
for i in INS:
    if i.mnemonic == "call" and i.op_str.startswith("0x"):
        try: all_funcs.add(int(i.op_str, 16))
        except: pass
all_funcs = sorted(all_funcs)
def func_of(va):
    return all_funcs[max(0, bisect.bisect_right(all_funcs, va) - 1)]

# 把指令按函数分组
func_insns = defaultdict(list)
for i in INS:
    func_insns[func_of(i.address)].append(i)

hits = []  # (func, addr, bit, kind, op_str)
for fn, ilist in func_insns.items():
    status_reg = None          # 存 word[+0x2c] 的寄存器
    base2c = set()             # esi=0x519894 等 → [reg] == +0x2c
    base0 = set()              # esi=0x519868 等 → [reg+0x2c] == +0x2c
    for ins in ilist:
        m, op = ins.mnemonic, ins.op_str
        low = op.lower()
        # 记录循环基址赋值
        mm = re.match(r'(e?[a-z]{2}),\s*0x(519868|519894)$', op)
        if mm:
            r = mm.group(1); v = int(mm.group(2), 16)
            (base2c if v == 0x519894 else base0).add(r)
        # 识别 word[..] 加载到 reg 且解析为 +0x2c
        # 形式: mov reg, word ptr [mem]
        if m == "mov":
            lm = re.match(r'(e?[a-z]{2}),\s*word ptr \[([^\]]+)\]', op)
            if lm:
                dst = lm.group(1); inside = lm.group(2)
                d = signed_disp(inside)
                breg = mem_base_reg(inside)
                is_status = (d == 0x2c) or (breg in base2c and d == 0) or (breg in base0 and d == 0x2c)
                if is_status and dst not in ("esp",):
                    status_reg = dst
        # SET/CLR：or/and（忽略 test=只读）
        if m in ("or", "and"):
            # 内存形式：or/and word/byte ptr [mem], imm
            mm = re.match(r'(?:word|byte) ptr \[([^\]]+)\],\s*(0x[0-9a-f]+|\d+)$', op)
            if mm:
                inside = mm.group(1); imm = int(mm.group(2), 16) if mm.group(2).startswith('0x') else int(mm.group(2), 10)
                d = signed_disp(inside); breg = mem_base_reg(inside)
                is_status = (d == 0x2c) or (breg in base2c and d == 0) or (breg in base0 and d == 0x2c)
                is_hi = (breg in base2c and d == 1) or (breg in base0 and d == 0x2d) or (d == 0x2d)
                if is_status:
                    if imm in (0x8000, 0x7fff):
                        hits.append((fn, ins.address, "bit15", "SET" if m=="or" else "CLR", op))
                    elif imm in (0x80, 0x7f) and not is_hi:
                        hits.append((fn, ins.address, "bit7", "SET" if m=="or" else "CLR", op))
                    elif imm in (0x80, 0x7f) and is_hi:
                        hits.append((fn, ins.address, "bit15", "SET" if m=="or" else "CLR", op))
            # 寄存器形式：or/and <status_reg_h or _l>, imm
            if status_reg:
                h = status_reg.replace("e", "")[0] + "h"   # eax->ah
                l = status_reg.replace("e", "")[0] + "l"   # eax->al
                rm = re.match(r'(ah|al|' + re.escape(h) + r'|' + re.escape(l) + r'),\s*(0x[0-9a-f]+|\d+)$', op)
                if rm:
                    regpart = rm.group(1); imm = int(rm.group(2), 16) if rm.group(2).startswith('0x') else int(rm.group(2), 10)
                    if imm in (0x8000, 0x7fff, 0x80, 0x7f):
                        bit = "bit15" if regpart in ("ah", h) else "bit7"
                        kind = "SET" if m == "or" else "CLR"
                        hits.append((fn, ins.address, bit, kind, op))

# 去重（同一 addr 可能重复）+ 聚类
seen = set(); uniq = []
for h in hits:
    if h[1] in seen: continue
    seen.add(h[1]); uniq.append(h)
by_func = defaultdict(list)
for h in uniq: by_func[h[0]].append(h)

print("SET/CLR 命中: %d  涉及函数: %d\n" % (len(uniq), len(by_func)))
for fn in sorted(by_func):
    lst = by_func[fn]
    kinds = sorted(set("%s:%s" % (b, k) for (_, _, b, k, _) in lst))
    anchors = set()
    for j in dis(fn, 0x300):
        if j.mnemonic == "call" and j.op_str.startswith("0x"):
            try:
                t = int(j.op_str, 16)
                if t in ANCHOR: anchors.add(ANCHOR[t])
            except: pass
    print("0x%06x  [%s]  %s" % (fn, " ".join(kinds), " ".join(sorted(anchors))))
    for (_, a, b, k, op) in sorted(lst):
        print("    0x%x  %-5s %s" % (a, "%s:%s" % (b, k), op))
