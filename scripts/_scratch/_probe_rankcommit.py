# -*- coding: utf-8 -*-
"""在 and al,0xf8 后找 or al,imm8 再 mov [..+0x2d],al 的 rank 写回序列。"""
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

sites = [0x41ac87, 0x41ac91, 0x41aca0, 0x44c0d8, 0x45d359, 0x4731a7,
         0x47fd5a, 0x49cb3c, 0x49cc17, 0x49d8ad]

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

out = []
for s in sites:
    o = s - BASE
    # 反汇编 s 起 0x40 字节
    asm = list(md.disasm(mem[o: o + 0x40], s))
    has_or = False
    or_imm = None
    has_write = False
    write_ins = None
    for j, ins in enumerate(asm):
        if ins.mnemonic == "or" and ins.op_str.startswith("al,"):
            has_or = True
            try:
                or_imm = int(ins.op_str.split(",")[1].strip(), 16)
            except Exception:
                pass
        if "0x2d" in ins.op_str and ins.mnemonic == "mov" and "al" in ins.op_str.split(",")[1]:
            has_write = True
            write_ins = ins
    out.append(f"\n--- site {s:#010x} ---")
    out.append(f"  has_or_al={has_or} or_imm={or_imm}  has_write_[..+0x2d],al={has_write}")
    for ins in asm[:14]:
        mark = ">>" if ins.address == s else "  "
        out.append(f"  {mark} {ins.address:#010x}  {ins.bytes.hex():<18} {ins.mnemonic:<8} {ins.op_str}")
    if has_write and write_ins:
        out.append(f"  *** WRITE: {write_ins.address:#010x} {write_ins.mnemonic} {write_ins.op_str}")

open(os.path.join(HERE, "_rankcommit.txt"), "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out[:120]))
