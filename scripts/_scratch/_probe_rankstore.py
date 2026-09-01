# -*- coding: utf-8 -*-
"""穷举 +0x2d 写入：mov byte[reg+0x2d],r8 (88 ?? 2d) 与 inc/dec byte[reg+0x2d] (fe ?? 2d)。"""
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

import struct, os, bisect
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
mem = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()

tg = set()
i = 0
while True:
    i = mem.find(b"\xe8", i)
    if i < 0:
        break
    rel = struct.unpack_from("<i", mem, i + 1)[0]
    t = (i + BASE) + 5 + rel
    if 0x401000 <= t < 0x4f0000:
        tg.add(t)
    i += 1
funcs = sorted(tg)
def host(va):
    k = bisect.bisect_right(funcs, va) - 1
    return funcs[k] if k >= 0 else 0

# mod=01 的 modrm: 0x40..0x7f ；rm 为 base 寄存器(0..7)。disp8 = 0x2d
# 88 /r : mov r/m8, r8 ; fe /0 : inc r/m8 ; fe /1 : dec r/m8
hits = []
o = 0
while o < len(mem) - 3:
    b0 = mem[o]
    if b0 in (0x88, 0x89, 0xfe):
        b1 = mem[o + 1]
        if (b1 & 0xC0) == 0x40 and mem[o + 2] == 0x2d:
            kind = {0x88: "mov8", 0x89: "mov32", 0xfe: "inc/dec"}[b0]
            hits.append((o, kind, b0, b1))
            o += 3
            continue
    o += 1

out = [f"=== +0x2d 写入签名 {len(hits)} 处 ==="]
# 按函数聚合
from collections import defaultdict
byfn = defaultdict(list)
for o, kind, b0, b1 in hits:
    byfn[host(BASE + o)].append((BASE + o, kind))
for fn in sorted(byfn):
    lst = byfn[fn]
    out.append(f"\nfunc {fn:#010x} ({len(lst)} 处):")
    for va, kind in lst[:8]:
        out.append(f"    {va:#010x}  {kind}")

# 反汇编最可疑的函数（含多处的）
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False
suspects = sorted(byfn, key=lambda f: -len(byfn[f]))[:6]
for fn in suspects:
    idx = funcs.index(fn)
    end = funcs[idx + 1] if idx + 1 < len(funcs) else fn + 0x300
    code = mem[fn - BASE: end - BASE]
    asm = list(md.disasm(code, fn))
    out.append(f"\n########## func {fn:#010x} ({len(asm)} 条) ##########")
    for ins in asm:
        if "+0x2d" in ins.op_str or "0x2d" in ins.op_str:
            out.append(f"  >>> {ins.address:#010x}  {ins.mnemonic} {ins.op_str}")
        if "0x2d" in ins.op_str and ("cmp" in ins.mnemonic or "mov" in ins.mnemonic or "and" in ins.mnemonic or "or" in ins.mnemonic):
            out.append(f"     {ins.address:#010x}  {ins.mnemonic} {ins.op_str}")

open(os.path.join(HERE, "_rankstore.txt"), "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out[:150]))
