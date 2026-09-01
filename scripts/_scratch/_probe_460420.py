
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
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import *

MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', "rb").read()
BASE = 0x400000

def va_of(off): return BASE + off
def off_of(va): return va - BASE

def disasm_at(va, nbytes=0x200, start=None):
    off = off_of(va)
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    code = MEM[off:off+nbytes]
    out = []
    for ins in md.disasm(code, va):
        line = f"{ins.address:08x}  {ins.bytes.hex():24s} {ins.mnemonic} {ins.op_str}"
        out.append(line)
    return out

def find_reads_writes(target_off, kind):
    """target_off = file offset of the accessed memory (e.g. 0x513ff6 - 0x400000)."""
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    hits = []
    off = 0
    while off < len(MEM) - 16:
        # only disassemble likely code by scanning whole image in chunks
        chunk = MEM[off:off+0x4000]
        try:
            for ins in md.disasm(chunk, BASE+off):
                for op in ins.operands:
                    if op.type == X86_OP_MEM:
                        mm = op.mem
                        base_reg = mm.base
                        disp = mm.disp
                        # reconstruct absolute addr if base==0 (no reg) or we just record disp as offset from seg 0
                        # For our purpose, find immediate disp that equals target_off
                        if mm.base == 0 and mm.index == 0 and disp == target_off:
                            hits.append((ins.address, kind, f"{ins.mnemonic} {ins.op_str}"))
        except Exception:
            pass
        off += 0x4000
    return hits

# 1) disassemble the three functions
for label, va in [("0x460420 ID->handler idx", 0x460420),
                 ("0x460500 count asked", 0x460500),
                 ("0x460530 rand slot", 0x460530)]:
    lines = disasm_at(va, 0x160)
    with open(f"F:/Games/Taikou 2/scripts/_f_{va:x}.txt", "w", encoding="utf-8") as f:
        f.write(f"=== {label} @ {va:08x} ===\n")
        f.write("\n".join(lines))
    print(f"[OK ] wrote _f_{va:x}.txt ({len(lines)} instrs)")

# 2) find writers/readers of 0x513ff6 and 0x513ff8
for tgt in (0x513ff6, 0x513ff8):
    rw = find_reads_writes(tgt - BASE, "both")
    with open(f"F:/Games/Taikou 2/scripts/_xref_{tgt:x}.txt", "w", encoding="utf-8") as f:
        f.write(f"=== accesses to {tgt:08x} (off {tgt-BASE:#x}) ===\n")
        if not rw:
            f.write("(none)\n")
        for a, k, s in rw:
            f.write(f"{a:08x}  {k}  {s}\n")
    print(f"[OK ] wrote _xref_{tgt:x}.txt ({len(rw)} hits)")
