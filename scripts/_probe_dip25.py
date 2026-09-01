# -*- coding: utf-8 -*-
"""正确提取 setter 调用前的三级 push (lv,b,a), 判定 lv 走向.
cdecl: push lv; push b; push a; call  -> call 前最近 3 个 push 即 (lv,b,a)."""
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

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

SETTERS = {0x49fe40: "set_diplo", 0x49ff10: "set_lord"}

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

def get_prev_pushes(site, n=3, window=0x60):
    """返回 call 前最近的 n 个 push 指令 (地址, 值或None, op_str)."""
    lo = max(0, rva(site) - window)
    inss = list(md.disasm(mem[lo: rva(site)], BASE + lo))
    pushes = []
    for ins in reversed(inss):
        if ins.mnemonic == "push":
            val = None
            m = re.match(r"^0x([0-9a-f]+)$", ins.op_str)
            if m:
                val = int(m.group(1), 16)
            pushes.append((ins.address, val, ins.op_str))
            if len(pushes) >= n:
                break
    return pushes  # 从近到远

def lv_kind(pushes, site):
    """push 顺序 (近->远) = (lv, b, a). lv 是第1个."""
    if not pushes:
        return "无push?"
    lv_addr, lv_val, lv_s = pushes[0]
    # 判断是否明显是等级立即数 (0..7 / 0..3)
    if lv_val is not None and lv_val <= 7:
        return f"push imm lv={lv_val} (固定等级)"
    # 否则 lv 来自寄存器 -> 看它是否 = getter结果 -1 / +1
    if lv_s in ("eax", "ax", "al"):
        # 往前找 getter 与 dec/inc
        # 在 pushes[0] 之前(地址更小)的反汇编窗口
        lo = max(0, rva(site) - 0x80)
        seg = list(md.disasm(mem[lo: rva(site)], BASE + lo))
        # 找 lv push 之前的指令
        idx = None
        for k, ins in enumerate(seg):
            if ins.address == lv_addr:
                idx = k; break
        seen_getter = False; seen_dec = False; seen_inc = False; seen_sub1 = False
        if idx is not None:
            for ins in seg[:idx]:
                if ins.mnemonic == "call" and ins.op_str in ("0x49fd60", "0x49fe70"):
                    seen_getter = True
                if ins.mnemonic == "dec" and ("ax" in ins.op_str):
                    seen_dec = True
                if ins.mnemonic == "inc" and ("ax" in ins.op_str):
                    seen_inc = True
                if ins.mnemonic == "sub" and re.search(r"ax.*,\s*1|eax.*,\s*1", ins.op_str):
                    seen_sub1 = True
        if seen_dec or seen_sub1:
            return "lv=eax, getter后DEC (变好!)"
        if seen_inc:
            return "lv=eax, getter后INC (恶化)"
        if seen_getter:
            return "lv=eax, getter后无调整 (维持?)"
        return "lv=寄存器(非ax?)"
    return f"lv={lv_s} (寄存器)"

for t, name in SETTERS.items():
    callers = find_e8_calls(t)
    print(f"\n{'='*64}\n{name} (0x{t:x}) — {len(callers)} 调用方 lv 提取\n{'='*64}")
    for site in sorted(callers):
        pushes = get_prev_pushes(site)
        kind = lv_kind(pushes, site)
        flag = ""
        if "变好" in kind: flag = "  <<<"
        elif "恶化" in kind: flag = "  (恶化)"
        # 打印三级 push
        ps = " | ".join(f"push {p[2]}" + (f"={p[1]}" if p[1] is not None else "") for p in pushes[:3])
        print(f"0x{site:x}: {kind}{flag}")
        print(f"   前3 push(近->远): {ps}")
