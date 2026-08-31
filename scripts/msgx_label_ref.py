#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续172（续171 下一步(B)）：给续170 的 3 个 MSG 置信消费函数补事件标签。
结论：3 个函数不是 3 个独立事件，而是「家臣/人事（登用·引抜·解雇·追放·離反·评定工作分配）」
对话子系统的 3 个入口点，共享同一 MSGX 消息池（主 dispatcher = 0x4d7fe0）。

方法：对每个目标函数，收集「函数本体 + 直接 callee（排除共享 setter 库 0x49a000-0x49cfff）」
内 push 的 MSGX id；再算每个函数的「独有」消息集（不在另两个函数中出现的）。

断言：
- 0x4a5010 / 0x4a5370 独有消息数 == 0  ⇒ 二者是薄包装入口，消息全部来自共享子系统。
- 0x4d7fe0 独有消息数 >> 0  ⇒ 它是主 dispatcher，承载全部人事消息池。
- 三者共享的通用工具消息集非空（#10/#15/#100/#255/#300/#500 等）。
"""
import os, json, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
msgx = json.load(open(os.path.join(HERE, "msgx_all_texts.json"), encoding="utf-8"))["texts"]
hexm = json.load(open(os.path.join(HERE, "hexmes_texts.json"), encoding="utf-8"))["texts"]
msgx_keys = set(int(k) for k in msgx.keys())
hexm_keys = set(int(k) for k in hexm.keys())

TARGETS = {
    "0x4a5010": "相性ベース 登用/引抜 A (薄包装入口)",
    "0x4a5370": "相性ベース 登用/引抜 B·寢返し/離反 (薄包装入口)",
    "0x4d7fe0": "家臣 解雇/追放/離反処理 = 人事主 dispatcher",
}
SETTER_LIB = (0x49a000, 0x49d000)

def dis(va, n):
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.skipdata = True
    off = va - BASE
    return list(md.disasm(bytes(MEM[off:off+n]), va))

def collect(va, depth, seen):
    ids = set()
    if va in seen:
        return ids
    seen.add(va)
    code = dis(va, 0xc00)
    callees = []
    for ins in code:
        if ins.mnemonic == "push" and ins.op_str.startswith("0x"):
            try:
                imm = int(ins.op_str, 16)
                if imm in msgx_keys or imm in hexm_keys:
                    ids.add(imm)
            except: pass
        if ins.mnemonic == "call" and ins.op_str.startswith("0x"):
            try:
                t = int(ins.op_str, 16)
                if SETTER_LIB[0] <= t < SETTER_LIB[1]:
                    continue
                callees.append(t)
            except: pass
    if depth > 0:
        for t in callees[:60]:
            ids |= collect(t, depth-1, seen)
    return ids

func_ids = {va: collect(int(va,16), 1, set()) for va in TARGETS}

def label(i):
    s = msgx.get(str(i)) or hexm.get(str(i)) or ""
    return s.replace("\n", " ")[:48]

print("=== 收集结果 ===")
for va, name in TARGETS.items():
    print(f"  {va} ({name}): {len(func_ids[va])} 个 MSGX id")

vas = list(TARGETS.keys())
distinct = {va: sorted(func_ids[va] - set().union(*[func_ids[o] for o in vas if o != va])) for va in vas}
shared = set.intersection(*[func_ids[v] for v in vas])

print("\n=== 断言 ===")
ok = True
for va in ["0x4a5010", "0x4a5370"]:
    n = len(distinct[va])
    print(f"  [{'PASS' if n==0 else 'FAIL'}] {va} 独有消息 = {n} (期望 0 = 薄包装)")
    ok = ok and n == 0
nd = len(distinct["0x4d7fe0"])
print(f"  [{'PASS' if nd>50 else 'FAIL'}] 0x4d7fe0 独有消息 = {nd} (期望 >>0 = 主 dispatcher)")
ok = ok and nd > 50
print(f"  [{'PASS' if len(shared)>0 else 'FAIL'}] 三者共享通用工具消息 = {len(shared)} 条")
ok = ok and len(shared) > 0

# 打印 0x4d7fe0 的关键事件簇（按 id 段归类，给中文事件标签）
print("\n=== 0x4d7fe0 主 dispatcher 关键消息簇（节选，给事件标签）===")
clusters = [
    (43, 66, "评定·工作分配与 rivalry（「这件事就交给你」「一比高下吧」）"),
    (178, 186, "叱責/失敗処分（「你都在做些什么呀」「再给我一次机会吧」）"),
    (1730, 1734, "昇進ライバル 対話（「你早我一步得到重用」「共同努力吧」）"),
    (388, 389, "勝負/腕試し（「这次在下赢了呀」「被我的成绩吓坏了吧」）"),
    (300, 300, "寛大処置への感謝（解雇/追放 軽減）"),
    (500, 500, "交渉/金銭提示（「那么，%u贯怎么样？」）"),
]
for lo, hi, desc in clusters:
    hits = [i for i in distinct["0x4d7fe0"] if lo <= i <= hi]
    if hits:
        print(f"  [{lo}-{hi}] {desc}: {len(hits)} 条，例 #{hits[0]} = {label(hits[0])}")

print("\nRESULT:", "ALL PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
