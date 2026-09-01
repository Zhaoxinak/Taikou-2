# -*- coding: utf-8 -*-
"""追关系「变好」写入点: 扫描两个 setter 的全部 e8 调用方,
分类调用前 eax 的走向 (inc/add=恶化, dec/sub=变好, push imm=固定/初始化)."""
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

import struct, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
mem = open(MEM_PATH, "rb").read()
N = len(mem)

def rva(p): return p - BASE
def rd(p, n): return mem[rva(p): rva(p)+n]
def at(p): return rva(p)

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

SETTERS = {0x49fe40: "set_diplo(外交8级)", 0x49ff10: "set_lord(主从4级)"}

# 1) 全映像 e8 调用方扫描
def find_e8_calls(target):
    out = []
    i = 0
    while i + 5 <= N:
        if mem[i] == 0xe8:
            rel = struct.unpack("<i", mem[i+1:i+5])[0]
            dst = (BASE + i + 5 + rel) & 0xffffffff
            if dst == target:
                out.append(BASE + i)
        i += 1
    return out

callers = {}
for t, name in SETTERS.items():
    callers[t] = find_e8_calls(t)
    print(f"[*] {name} (0x{t:x}) e8 调用方: {len(callers[t])} 处")

# 2) 对每个调用方, 反汇编前 0x60 字节, 抽取 eax 调整方向
def disasm_around(site, pre=0x60, post=8):
    lo = max(0, rva(site) - pre)
    code = mem[lo: rva(site) + post]
    res = []
    for ins in md.disasm(code, BASE + lo):
        res.append(ins)
    return res

def classify(inss, site):
    """返回 (direction, notes): inc/add / dec/sub / imm / getter+? / unknown"""
    # 找 site 这条 call 在 inss 中的索引
    idx = None
    for k, ins in enumerate(inss):
        if ins.address == site:
            idx = k
            break
    if idx is None:
        return "unknown", ["call 不在反汇编窗口"]
    # 向前看 call 之前的指令, 关注 eax/ax 的修改
    notes = []
    eax_dir = None
    saw_getter_diplo = False
    saw_getter_lord = False
    saw_push_imm = False
    push_val = None
    # 从 idx-1 往回扫到函数开头标志(ret/push ebp)或窗口边界
    j = idx - 1
    while j >= 0:
        s = inss[j]
        op = s.mnemonic
        ops = s.op_str
        # 直接 push 立即数给 setter 的情形
        if op == "push" and re.match(r"^0x[0-9a-f]+$", ops):
            saw_push_imm = True
            push_val = int(ops, 16)
            notes.append(f"  push imm 0x{push_val:x} (可能直接等级值)")
            # push 通常是最后一步, 往前不再影响
            break
        # getter 调用
        if op == "call" and ops in ("0x49fd60", "0x49fe70"):
            if ops == "0x49fd60":
                saw_getter_diplo = True
            else:
                saw_getter_lord = True
            notes.append(f"  call {ops} (getter)")
            # getter 之后通常紧跟 eax 调整
            # 看 getter 之后到 call 之间
            seg = inss[j+1: idx]
            for g in seg:
                gm, go = g.mnemonic, g.op_str
                if gm in ("inc", "add") and ("ax" in go or go in ("eax",)):
                    eax_dir = "inc/add(恶化)"
                elif gm in ("dec", "sub") and ("ax" in go or "eax" in go):
                    eax_dir = "dec/sub(变好)"
            break
        # 独立的 eax 调整 (没经过 getter, 直接算偏移)
        if op in ("inc", "add") and ("ax" in ops or ops == "eax"):
            eax_dir = "inc/add(恶化)"
        elif op in ("dec", "sub") and ("ax" in ops or ops == "eax"):
            eax_dir = "dec/sub(变好)"
        j -= 1
    if eax_dir:
        notes.append(f"  => eax 方向: {eax_dir}")
        return eax_dir, notes
    if saw_push_imm:
        return "push_imm", notes
    if saw_getter_diplo or saw_getter_lord:
        return "getter_no_adj?", notes
    return "unknown", notes

# 3) 输出分类
for t, name in SETTERS.items():
    print(f"\n{'='*70}\n{name} (0x{t:x}) — {len(callers[t])} 调用方分类\n{'='*70}")
    for site in sorted(callers[t]):
        inss = disasm_around(site)
        direction, notes = classify(inss, site)
        flag = ""
        if "变好" in direction:
            flag = "  <<< 关系变好候选"
        elif "恶化" in direction:
            flag = "  (恶化)"
        elif "push_imm" in direction:
            flag = "  (固定值/初始化)"
        print(f"0x{site:x}: {direction}{flag}")
        for n in notes:
            print(n)
