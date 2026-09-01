
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
mem=open(_ROOT + '/scripts/_unpacked_mem.bin',"rb").read()
BASE=0x400000
def disasm(va, length, stop_ret=False):
    md=Cs(CS_ARCH_X86, CS_MODE_32); md.detail=True
    for ins in md.disasm(mem[va-BASE: va-BASE+length], va):
        print(f"{ins.address:08x}  "+" ".join(f"{b:02x}" for b in ins.bytes).ljust(18)+f"{ins.mnemonic} {ins.op_str}")
        if stop_ret and ins.mnemonic=='ret': break

print("===== 0x492b60 LoadNpkEntry =====")
disasm(0x492b60, 0x300, stop_ret=True)
