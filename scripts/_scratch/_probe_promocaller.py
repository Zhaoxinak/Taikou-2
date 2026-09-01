# -*- coding: utf-8 -*-
"""找 0x45d300 的调用方，并反汇编之；同时找 0x43dd50(复制rank) 的调用方。"""
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

def callers(target):
    pat = struct.pack("<i", (target - BASE) - 5 - (0))  # placeholder
    # call 编码：E8 rel ; rel = target - (site+5); site = target - 5 - rel
    # 找所有 E8 后 rel 使 site+5+rel = target
    out = []
    o = 0
    while o < len(mem) - 5:
        if mem[o] == 0xe8:
            rel = struct.unpack_from("<i", mem, o + 1)[0]
            t = (o + BASE) + 5 + rel
            if t == target:
                out.append(BASE + o)
        o += 1
    return out

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False
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

out = []
for tgt in (0x45d300, 0x43dd50):
    cs = callers(tgt)
    out.append(f"\n=== callers of {tgt:#010x} : {len(cs)} ===")
    fns = sorted(set(host(c) for c in cs))
    out.append("  funcs: " + " ".join(hex(f) for f in fns))
    # 反汇编第一个调用方
    if fns:
        fn = fns[0]
        idx = funcs.index(fn)
        end = funcs[idx + 1] if idx + 1 < len(funcs) else fn + 0x400
        code = mem[fn - BASE: end - BASE]
        asm = list(md.disasm(code, fn))
        out.append(f"\n########## caller {fn:#010x} ({len(asm)} 条) ##########")
        for ins in asm:
            mark = ">>" if ins.address in cs else "  "
            out.append(f"  {mark} {ins.address:#010x}  {ins.bytes.hex():<18} {ins.mnemonic:<8} {ins.op_str}")

open(os.path.join(HERE, "_promo_caller.asm"), "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out[:160]))
