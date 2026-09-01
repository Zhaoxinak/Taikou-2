"""Find call-sites of each flag setter, capture preceding push arg. (fixed VA handling)"""
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

import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x400000
BIN = _ROOT + '/scripts/_unpacked_mem.bin'
data = open(BIN, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True
md.skipdata = True

targets = {
    0x42c140: "mode_m1    -> 0x511bf8",
    0x43cb20: "mode_m2_a  -> 0x51352c",
    0x43cfc0: "mode_m2_b  -> 0x51352c(toggle)",
    0x43ca70: "parity_a   -> 0x513540",
    0x43ca90: "parity_b   -> 0x513540",
    0x43ca20: "battle_type-> 0x513548",
    0x43cb70: "handle_stat-> 0x513534",
}

def find_calls(tgt):
    res = []
    n = len(data) - 5
    for p in range(n):
        if data[p] != 0xE8:
            continue
        rel = struct.unpack_from("<i", data, p+1)[0]
        next_ip_off = p + 5
        tgt_va = (next_ip_off + rel) + BASE
        if tgt_va == tgt:
            res.append(p + BASE)  # VA of the call instruction
    return res

def disasm_backward(call_va, nbytes=0x50):
    start = call_va - nbytes
    code = data[start-BASE: call_va-BASE]
    return [(ins.address, ins.mnemonic, ins.op_str) for ins in md.disasm(code, start)]

for tgt, name in targets.items():
    sites = find_calls(tgt)
    print(f"\n##### {name}  ({len(sites)} call sites) #####")
    for call_va in sites:
        ctx = disasm_backward(call_va, 0x48)
        print(f"  -- at {call_va:#08x} --")
        for a, m, o in ctx[-7:]:
            mark = "  <== CALL" if a == call_va else ""
            print(f"     {a:#08x}  {m} {o}{mark}")
