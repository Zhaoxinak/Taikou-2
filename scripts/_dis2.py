
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
IMG = open(_ROOT + '/scripts/_unpacked_mem.bin','rb').read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def dis(va, nbytes):
    off = va - BASE
    code = IMG[off:off+nbytes]
    print(f"\n===== func 0x{va:x}  (until ret / {nbytes}B) =====")
    for ins in md.disasm(code, va):
        print(f"0x{ins.address:x}  " + ins.mnemonic + "  " + ins.op_str)
        if ins.mnemonic == 'ret' or ins.mnemonic == 'retn':
            break

for a in (0x47da10, 0x47da50, 0x47d960):
    dis(a, 80)
