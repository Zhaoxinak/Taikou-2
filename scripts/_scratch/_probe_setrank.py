# -*- coding: utf-8 -*-
"""反汇编 0x435740（疑似任命/设置rank提交函数）与其调用方 0x435570 关键段。"""
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

import os, bisect, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
mem = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
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

def disasm(va, maxlen=0x300):
    fn = host(va)
    idx = funcs.index(fn)
    end = funcs[idx + 1] if idx + 1 < len(funcs) else fn + maxlen
    code = mem[fn - BASE: end - BASE]
    return fn, list(md.disasm(code, fn))

out = []
try:
    for va in (0x435740,):
        fn, asm = disasm(va)
        out.append(f"\n########## 0x435740  func={fn:#010x} ({len(asm)} 条) ##########")
        for ins in asm:
            mark = ""
            if "+0x2d" in ins.op_str or "0x2d" in ins.op_str or "0x50d850" in ins.op_str or "0x504780" in ins.op_str:
                mark = " >>"
            out.append(f"  {mark} {ins.address:#010x}  {ins.bytes.hex():<18} {ins.mnemonic:<8} {ins.op_str}")
except Exception:
    import traceback
    out.append("ERROR:\n" + traceback.format_exc())

open(os.path.join(HERE, "_setrank.asm"), "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out[:200]))
