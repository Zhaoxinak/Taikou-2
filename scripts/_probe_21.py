# -*- coding: utf-8 -*-
"""追 +0x21 setter (0x49a630) 的全部调用方, 看传值与周边字段。"""
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>

import re, struct
from collections import Counter
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
mem = open(MEM, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def e8_callers(target):
    hits = []
    for i in range(len(mem) - 5):
        if mem[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", mem, i + 1)[0]
        if (BASE + i + 5 + rel) & 0xFFFFFFFF == target:
            hits.append(BASE + i)
    return hits


def ctx(addr, back=26):
    o = addr - BASE
    st = max(0, o - 130)
    seq = []
    for ins in md.disasm(mem[st:o + 6], BASE + st):
        seq.append((ins.address, ins.mnemonic, ins.op_str))
        if len(seq) > 120:
            seq.pop(0)
    idx = next((k for k, s in enumerate(seq) if s[0] == addr), None)
    return seq[max(0, (idx or 0) - back): (idx or 0) + 2]


sites = e8_callers(0x49A630)
print("=" * 86)
print(f"A. 0x49a630 (+0x21 setter) 调用点 {len(sites)} 处")
print("=" * 86)

def owner(addr, starts):
    best = None
    for s in starts:
        if s <= addr:
            best = s
    return best


# 函数起点候选: 所有 call/jmp 目标
starts = set()
for i in range(len(mem) - 5):
    if mem[i] == 0xE8:
        rel = struct.unpack_from("<i", mem, i + 1)[0]
        starts.add((BASE + i + 5 + rel) & 0xFFFFFFFF)
starts = sorted(starts)

fn = Counter(owner(s, starts) for s in sites)
print(f"\n  按所属函数归并: {len(fn)} 个函数")
for f, n in fn.most_common(20):
    print(f"    {f:#010x}  x{n}")

print("\n" + "=" * 86)
print("B. 调用点上下文（每个函数取 1 个代表，最多 14 个）")
print("=" * 86)
seen = set()
for s in sites:
    f = owner(s, starts)
    if f in seen:
        continue
    seen.add(f)
    if len(seen) > 14:
        break
    print(f"\n  --- {s:08x}  (函数 {f:#010x}) ---")
    for ad, m, p in ctx(s):
        mark = " <<<" if ad == s else ""
        print(f"    {ad:08x}  {m:<8} {p}{mark}")

print("\n" + "=" * 86)
print("C. 写入 +0x21 前 push 的值来源统计")
print("=" * 86)
src = Counter()
for s in sites:
    seq = ctx(s, 6)
    pre = " | ".join(f"{m} {p}" for a, m, p in seq if a < s)
    if re.search(r"movzx|mov\s+\w+,\s*byte ptr", pre):
        src["从 byte 字段零扩展"] += 1
    if re.search(r"push\s+(0x[0-9a-f]+|\d+)", pre):
        src["push 立即数"] += 1
    if re.search(r"call\s+0x", pre):
        src["call 返回值"] += 1
    if re.search(r"mov\s+e\w+,\s*dword ptr \[esp", pre):
        src["来自栈参数"] += 1
    if "+ 0x21]" in pre or "+ 0x20]" in pre or "+ 0x29]" in pre or "+ 0x25]" in pre:
        src["读邻近尾段字段"] += 1
for k, v in src.most_common():
    print(f"    {k}: {v}")

print("\n" + "=" * 86)
print("D. 与 +0x21 出现在同一函数里的其它尾段字段")
print("=" * 86)
TAIL = {0x20: "0x49a650", 0x21: "0x49a630", 0x22: "0x49a670", 0x23: "0x49a690",
        0x24: "0x49a750", 0x25: "0x49a760", 0x26: "0x49a770", 0x28: "0x49a790",
        0x29: "0x49a7b0", 0x2a: "0x49a7d0", 0x2e: "0x49a880"}
for off, ent in TAIL.items():
    ss = set(e8_callers(int(ent, 16)))
    common_fns = {owner(x, starts) for x in sites} & {owner(x, starts) for x in ss}
    print(f"    +{off:#04x} ({ent}): 与 +0x21 共有 {len(common_fns)} 个调用函数")
