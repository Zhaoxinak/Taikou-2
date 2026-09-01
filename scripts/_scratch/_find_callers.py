
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
md=Cs(CS_ARCH_X86, CS_MODE_32)
TARGETS={0x441580,0x4414d0,0x4411b0}
hits={t:[] for t in TARGETS}
for ins in md.disasm(mem, 0x400000):
    if ins.mnemonic=='call' and ins.op_str.startswith('0x'):
        t=int(ins.op_str,16)
        if t in TARGETS:
            hits[t].append(ins.address)
for t in TARGETS:
    print(f"callers of {t:#x}: {[hex(x) for x in hits[t][:10]]}")
