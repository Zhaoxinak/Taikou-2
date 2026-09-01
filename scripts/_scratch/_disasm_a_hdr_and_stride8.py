
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
DATA = open(_ROOT + '/scripts/_unpacked_mem.bin','rb').read()
BASE = 0x400000
cs = Cs(CS_ARCH_X86, CS_MODE_32)
def disasm(va, nbytes):
    return list(cs.disasm(DATA[va-BASE:va-BASE+nbytes], va))
def show(name, va, nbytes):
    print(f"\n===== {name} @0x{va:06x} =====")
    for ins in disasm(va, nbytes):
        print(f"  0x{ins.address:06x}: {ins.mnemonic} {ins.op_str}")
show("A-hdr reader 0x439060", 0x439060, 0xb0)
show("stride-8 fn 0x439130", 0x439130, 0xc0)
