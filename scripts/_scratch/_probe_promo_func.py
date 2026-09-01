# -*- coding: utf-8 -*-

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
import struct, os, bisect, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
mem = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()

log = []
try:
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
    log.append(f"call-targets={len(funcs)}")

    def host(va):
        k = bisect.bisect_right(funcs, va) - 1
        return funcs[k] if k >= 0 else 0

    start = host(0x4e88b8)
    idx = funcs.index(start)
    end = funcs[idx + 1]
    log.append(f"0x4e88b8 host start={start:#010x} end={end:#010x} size={end-start}")

    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False
    code = mem[start - BASE: end - BASE]
    asm = []
    for ins in md.disasm(code, start):
        asm.append(f"{ins.address:#010x}  {ins.bytes.hex():<18} {ins.mnemonic:<8} {ins.op_str}")
    log.append(f"disasm {len(asm)} instrs")
    txt = "\n".join(asm)
    open(os.path.join(HERE, "_promo_func.asm"), "w", encoding="utf-8").write(txt)

    uses = [ln for ln in asm if "0x50d850" in ln or "50d850" in ln]
    log.append(f"\n--- uses of 0x50d850 ({len(uses)}) ---")
    for u in uses:
        log.append(u)
except Exception:
    log.append("ERROR:\n" + traceback.format_exc())

open(os.path.join(HERE, "_probe_promo_func.log"), "w", encoding="utf-8").write("\n".join(log))
