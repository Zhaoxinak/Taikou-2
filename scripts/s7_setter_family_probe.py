#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe: 在 0x49bf00..0x49c100 区域枚举 S7 16B 条目的 setter 族。
   每函数以 ecx=base，找 `mov [ecx+off], ...` 写点，按函数(以 ret 4/ret 切分)归组。
   输出每个函数写入的字段偏移集合 —— 形成 S7 全字段 setter 地图。
"""
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

import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x400000
BIN  = _ROOT + '/scripts/_unpacked_mem.bin'
START, END = 0x49bf00, 0x49c100

def load():
    with open(BIN, "rb") as f:
        return f.read()

def main():
    b = load()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False
    off0 = START - BASE
    code = b[off0:END-BASE]
    # 反汇编整段，记录每条指令的 VA
    insns = []
    for ins in md.disasm(code, START):
        insns.append(ins)

    # 按函数切分：遇到 ret/ret imm/iret 等结束。简化：以 ret 4 / ret 切分。
    funcs = []
    cur = []
    for ins in insns:
        cur.append(ins)
        m = ins.mnemonic
        if m in ("ret", "retf", "iret", "iretd"):
            if cur:
                funcs.append(cur)
            cur = []
    if cur:
        funcs.append(cur)

    # 找 mov [ecx+off], X 写点
    import re
    results = []
    for fn in funcs:
        fstart = fn[0].address
        writes = set()
        for ins in fn:
            o = ins.op_str
            # 匹配 ecx + 0xNN 或 ecx + NN 作为目标
            m = re.search(r"word ptr \[ecx \+ (0x[0-9a-f]+|\d+)\]", o)
            if m and (ins.mnemonic.startswith("mov") or ins.mnemonic in ("add","sub","and","or","xor")):
                val = int(m.group(1), 0)
                if val < 16:
                    writes.add(val)
        if writes:
            results.append((fstart, sorted(writes)))

    print(f"S7 setter 族扫描 @ 0x{START:x}..0x{END:x}: {len(results)} 个函数含 ecx+<16 写点")
    for fstart, offs in results:
        # 简单判断：是否带 ret 4（stdcall 参数）=> 参数化 setter
        tail = " ".join(i.mnemonic for i in funcs[[x[0] for x in results].index(fstart)])
        print(f"  0x{fstart:x}  写字段 {offs}  ({'ret4' if 'ret' in tail else '?'})")

if __name__ == "__main__":
    main()
