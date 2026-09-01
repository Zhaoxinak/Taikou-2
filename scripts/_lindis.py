
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
import sys, struct
from capstone import *
MEM=open(_ROOT + '/scripts/_unpacked_mem.bin',"rb").read(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32)
start=int(sys.argv[1],16); n=int(sys.argv[2],16)
off=start-BASE
for ins in md.disasm(MEM[off:off+n], start):
    tgt=''
    if ins.mnemonic=='call' and ins.op_str.startswith('0x'): tgt='   ; call'
    print(f"0x{ins.address:06x}  {ins.bytes.hex():<20s} {ins.mnemonic:<8s} {ins.op_str}{tgt}")
