"""Disassemble battle-mode flag setters + caller context (capstone)."""
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

import struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x400000
BIN = _ROOT + '/scripts/_unpacked_mem.bin'
data = open(BIN, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True
md.skipdata = True

def at(va):
    return data[va - BASE:]

def disasm(va, maxlen=0x200):
    out = []
    code = at(va)
    for ins in md.disasm(code, va):
        out.append((ins.address, ins.mnemonic, ins.op_str))
        if ins.mnemonic == "ret" or ins.mnemonic.startswith("ret"):
            break
        if len(out) * 1 > maxlen:
            break
    return out

def show(va, label, maxlen=0x200):
    print(f"\n=== {label} @ {va:#x} ===")
    for a, m, o in disasm(va, maxlen):
        print(f"  {a:#08x}  {m} {o}")

def show_range(va, nbytes=0x60):
    print(f"\n=== range @ {va:#x} (+{nbytes:#x}) ===")
    code = at(va)[:nbytes]
    for ins in md.disasm(code, va):
        print(f"  {ins.address:#08x}  {ins.mnemonic} {ins.op_str}")

# Flag setters
setters = {
    "mode_m1":    0x42c140,
    "mode_m2_a":  0x43cb20,
    "mode_m2_b":  0x43cfc0,
    "parity_a":   0x43ca70,
    "parity_b":   0x43ca90,
    "battle_type":0x43ca20,
    "handle_stat":0x43cb70,
}
for name, va in setters.items():
    show(va, name, maxlen=0x120)

# Caller contexts (around the setter call-site) to see the value passed
callers = {
    "mode_m1<-0x427000": 0x427000,
    "mode_m1<-0x42e000": 0x42e000,
    "mode_m1<-0x433000": 0x433000,
    "mode_m2_a<-0x433000":0x433000,
    "mode_m2_a<-0x43d000":0x43d000,
    "mode_m2_b<-0x434000":0x434000,
    "parity_a<-0x433000": 0x433000,
    "parity_b<-0x434000": 0x434000,
    "battle_type<-0x422000":0x422000,
    "battle_type<-0x434000":0x434000,
    "handle_stat<-0x434000":0x434000,
}
for name, va in callers.items():
    show_range(va, 0x80)
