# -*- coding: utf-8 -*-
"""_p89.py — 模式标志 setter/setter caller xref（P1 #89）"""
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

import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMG = open(_ROOT + '/scripts/_unpacked_mem.bin', "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.skipdata = True

FLAGS = {
    "mode_m1": 0x511bf8,
    "mode_m2": 0x51352c,
    "parity": 0x513540,
    "battle_type": 0x513548,
    "handle_stat": 0x513534,
}
# 找写点：mov [addr], reg  （含 dword ptr）
def find_writes(addr):
    out = []
    a = addr - BASE
    # 直接扫描二进制：寻找 'C7 05 <4B> xx' (mov dword [imm32], imm32) 或 '89 05 <4B>' / 'A3 <4B>'
    pats = []
    b = addr.to_bytes(4, "little")
    # A3 xx xx xx xx  : mov [imm32], eax
    pats.append((b"\xa3" + b, "mov [imm],eax"))
    # 89 /r : mov [imm32], r32  => opcodes C7 05 .. or 89 05 ..
    # we scan generically:
    return out

# 更稳：逐指令反汇编，匹配 'dword ptr [0xADDR]' 出现在写操作
def scan():
    # 把镜像分段反汇编（粗扫）
    writes = {k: [] for k in FLAGS}
    reads = {k: [] for k in FLAGS}
    step = 0x2000
    for va in range(BASE, BASE + len(IMG), step):
        try:
            code = IMG[va - BASE: va - BASE + step]
        except Exception:
            continue
        for r in md.disasm(code, va):
            s = "%s %s" % (r.mnemonic, r.op_str)
            for k, ad in FLAGS.items():
                hexad = "0x%x" % ad
                if hexad in s:
                    if r.mnemonic in ("mov",) and "]" in s and hexad in s.split(",")[0]:
                        # 写：目标是 [addr]
                        if "ptr [0x%x]" % ad in s and ", " in s and not s.strip().endswith("[0x%x]" % ad):
                            writes[k].append((va, s))
                    # 读：源是 [addr]
                    if "ptr [0x%x]" % ad in s and s.strip().startswith("mov") and "ptr [0x%x]" % ad in s.split(",")[1] if "," in s else False:
                        reads[k].append((va, s))
    return writes, reads

writes, reads = scan()
for k in FLAGS:
    print("==== %s @0x%x ====" % (k, FLAGS[k]))
    print("  writes(%d):" % len(writes[k]))
    for va, s in writes[k][:12]:
        print("    0x%x: %s" % (va, s))
    print("  reads(%d):" % len(reads[k]))
    for va, s in reads[k][:12]:
        print("    0x%x: %s" % (va, s))
