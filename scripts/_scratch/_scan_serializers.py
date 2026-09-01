#!/usr/bin/env python3
"""Scan serializer region for XOR-stream read calls and capture target globals.
For each call to 0x47d910 (READ1B wrapper) / 0x47d930 (READ2B wrapper),
the destination global is the immediate pushed just before the call.
Prints function-ish grouping by 'ret' boundaries.
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
START, END = 0x47dae0, 0x47f1c0

data = open(BIN, "rb").read()
off0 = START - BASE
code = data[off0:off0 + (END - START)]
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

PRIM = {0x47d910: "R1", 0x47d930: "R2"}

def is_global_imm(v):
    return 0x500000 <= v <= 0x52ffff

print(f"# serializer scan {START:#x}..{END:#x}")
func_start = START
pending = None  # (value, addr_of_push)
instrs = list(md.disasm(code, START))
i = 0
for ins in instrs:
    if ins.address >= END:
        break
    mnem, ops = ins.mnemonic, ins.op_str
    # record a push of a global immediate
    if mnem == "push" and ops.startswith("0x"):
        v = int(ops, 16)
        if is_global_imm(v):
            pending = (v, ins.address)
        else:
            pending = None
    elif mnem == "call" and ops.startswith("0x"):
        t = int(ops, 16)
        if t in PRIM:
            tgt = f"{pending[0]:#x}" if pending else "?"
            pp = f" (push@{pending[1]:#x})" if pending else ""
            print(f"{ins.address:#010x}  {PRIM[t]} -> {tgt}{pp}")
            pending = None
    elif mnem == "ret" or mnem == "retn":
        print(f"--- ret @ {ins.address:#x} (likely func boundary) ---")
        pending = None
    else:
        pending = None
