#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""反汇编战斗模拟簇(0x438c00..0x43a700)，定位单位实例(0x512b60)字段的来源：
   - 标注所有写 0x512b60 的指令
   - 标注所有从静态地址 0x5xxxxx 的读（候选静态数值表）
   - 标注 push 字面量 / mov reg, imm（可能的直接数值赋值）
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

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BIN = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000

def load():
    with open(BIN, "rb") as f:
        return f.read()

def main():
    data = load()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    va0, va1 = 0x438c00, 0x43a700
    off = va0 - BASE
    chunk = data[off: va1 - BASE]
    unit_hits = []
    static_reads = {}
    for ins in md.disasm(chunk, va0):
        s = ins.mnemonic + " " + ins.op_str
        # 写 0x512b60 (+disp)
        if "0x512b60" in s or (("0x512b" in s) and ("60" in s)):
            unit_hits.append((ins.address, ins.bytes.hex(), s))
        # 从静态地址读 (0x5xxxxx)
        import re
        for m in re.findall(r"0x5[0-9a-f]{4,5}", s):
            val = int(m, 16)
            if 0x500000 <= val <= 0x52ffff:
                static_reads.setdefault(val, []).append((ins.address, s))
    print(f"写 0x512b60 的指令数: {len(unit_hits)}")
    for va, b, s in unit_hits[:40]:
        print(f"  0x{va:08x}  {b:<20} {s}")
    print(f"\n从静态区 0x500000-0x52ffff 读的不同地址数: {len(static_reads)}")
    # 只显示出现 >=3 次的静态地址（更可能是数据表基地址）
    freq = sorted(static_reads.items(), key=lambda kv: -len(kv[1]))
    print("出现次数最多的静态读地址（候选数据表）：")
    for addr, lst in freq[:25]:
        print(f"  0x{addr:08x}  x{len(lst)}")
        for va, s in lst[:3]:
            print(f"      0x{va:08x}  {s}")

if __name__ == "__main__":
    main()
