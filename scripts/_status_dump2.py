#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续171：完整反汇编关键 SET 站点函数 + 直接调用方，定位玩法语义。"""
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

import os, bisect
from collections import defaultdict
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()

def dis(va, n):
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.skipdata = True
    off = va - BASE
    return list(md.disasm(bytes(MEM[off:off+n]), va))

INS = dis(BASE, len(MEM))
all_funcs = set([0x4f44b0, 0x400000])
for i in INS:
    if i.mnemonic == "call" and i.op_str.startswith("0x"):
        try: all_funcs.add(int(i.op_str, 16))
        except: pass
all_funcs = sorted(all_funcs)
def func_of(va): return all_funcs[max(0, bisect.bisect_right(all_funcs, va) - 1)]
func_insns = defaultdict(list)
for i in INS: func_insns[func_of(i.address)].append(i)

callers = defaultdict(set)
for fn, ilist in func_insns.items():
    for j in ilist:
        if j.mnemonic == "call" and j.op_str.startswith("0x"):
            try: callers[int(j.op_str,16)].add(fn)
            except: pass

def dump(fn, n=0x300, label=""):
    print("#"*78)
    print("# 函数 0x%06x %s  调用方: %s" % (fn, label, " ".join("0x%06x"%c for c in sorted(callers[fn])[:12])))
    print("#"*78)
    for ins in dis(fn, n):
        print("  0x%x  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
    print()

# bit15 SET 站点
dump(0x457a10, 0x200, "[bit15 SET or 0x8000]")
dump(0x439190, 0x400, "[bit15 SET+CLR, +0x2b&0xc0==0x40]")
# bit7 SET 站点
dump(0x48fb00, 0x200, "[bit7 SET or 128]")
dump(0x43dd20, 0x80,  "[bit7 布尔 setter]")
