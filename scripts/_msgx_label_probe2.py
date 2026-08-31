#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续171 下一步(B) 精修：3 个 MSG 置信函数的事件标签。
对每个目标函数，收集「函数本体 + 直接 callee（排除共享 setter 库 0x49a000-0x49cfff）」
内 push 的 MSGX id；再算每个函数的「独有」消息集（不在另两个函数中出现），给出事件标签。
"""
import os, json
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
msgx = json.load(open(os.path.join(HERE, "msgx_all_texts.json"), encoding="utf-8"))["texts"]
hexm = json.load(open(os.path.join(HERE, "hexmes_texts.json"), encoding="utf-8"))["texts"]
msgx_keys = set(int(k) for k in msgx.keys())
hexm_keys = set(int(k) for k in hexm.keys())

TARGETS = {
    "0x4a5010": "相性ベース 登用/引抜 A",
    "0x4a5370": "相性ベース 登用/引抜 B·寢返し/離反",
    "0x4d7fe0": "家臣 解雇/追放/離反処理",
}
SETTER_LIB = (0x49a000, 0x49d000)  # 排除共享 setter/方法库

def dis(va, n):
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.skipdata = True
    off = va - BASE
    return list(md.disasm(bytes(MEM[off:off+n]), va))

def collect(va, depth, seen):
    """返回该函数（及一层 callee）push 的 MSGX id 集合。"""
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

func_ids = {}
for va_s, name in TARGETS.items():
    va = int(va_s, 16)
    ids = collect(va, 1, set())
    func_ids[va_s] = ids
    print(f"{va_s} ({name}): 收集 MSGX id {len(ids)} 个")

print("\n=== 各函数独有消息（不在另两个函数中出现的）===")
vas = list(TARGETS.keys())
for va_s in vas:
    others = set().union(*[func_ids[o] for o in vas if o != va_s])
    distinct = sorted(func_ids[va_s] - others)
    print(f"\n## {va_s} {TARGETS[va_s]}  独有 {len(distinct)} 条")
    for i in distinct[:40]:
        src = msgx.get(str(i)) or hexm.get(str(i))
        if src is None:
            continue
        print(f"   #{i}: {src.replace(chr(10),' ')[:70]}")

# 共享（三函数都出现）= 通用工具消息，单独列出
allthree = set.intersection(*[func_ids[v] for v in vas])
print(f"\n=== 三函数共享（通用工具）消息 {len(allthree)} 条 ===")
for i in sorted(allthree):
    src = msgx.get(str(i)) or hexm.get(str(i))
    print(f"   #{i}: {src.replace(chr(10),' ')[:60]}")
