# -*- coding: utf-8 -*-
"""找 rank 写回（累加器形式 and al,0xf8 / or al,imm / mov [..+0x2d],al）。"""
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

out = []
# 1) and al, 0xf8
out.append("=== and al,0xf8 (24 f8) ===")
h = 0
hits24 = []
while True:
    h = mem.find(b"\x24\xf8", h)
    if h < 0:
        break
    hits24.append(BASE + h)
    h += 1
out.append(f"  {len(hits24)} 处: " + " ".join(hex(x) for x in hits24[:30]))
fns = sorted(set(host(x) for x in hits24))
out.append(f"  涉及函数 {len(fns)}: " + " ".join(hex(f) for f in fns))

# 2) 在这些函数里反汇编，找 rank 设置上下文：+0x2d 读取/写入 + merit(cmp) + or al,imm
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False
for fn in fns:
    idx = funcs.index(fn)
    end = funcs[idx + 1] if idx + 1 < len(funcs) else fn + 0x300
    code = mem[fn - BASE: end - BASE]
    asm = list(md.disasm(code, fn))
    # 找 and al,0xf8 出现的位置
    anchors = [ins.address for ins in asm if ins.bytes[:2] == b"\x24\xf8"]
    for a in anchors:
        # 取 a 附近 [-12, +40] 指令
        win = []
        for ins in asm:
            if a - 0x30 <= ins.address <= a + 0x60:
                win.append(ins)
        out.append(f"\n--- func {fn:#010x} @ {a:#010x} (and al,0xf8) ---")
        for ins in win:
            mark = ">>>" if ins.address == a else "   "
            out.append(f"  {mark} {ins.address:#010x}  {ins.bytes.hex():<18} {ins.mnemonic:<8} {ins.op_str}")

open(os.path.join(HERE, "_rankwrite2.txt"), "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out[:200]))
