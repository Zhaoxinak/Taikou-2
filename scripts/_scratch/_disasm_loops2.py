
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
mem=open(_ROOT + '/scripts/_unpacked_mem.bin',"rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)
def dump(s,e,label):
    print("\n==== %s 0x%x-0x%x ===="%(label,s,e))
    for ins in md.disasm(mem[s-base:e-base],s):
        if ins.address>e: break
        print("%08x  %-9s %s"%(ins.address,ins.mnemonic,ins.op_str))
# first loop around 0x4e8625 (call 0x47fc60)
dump(0x4e8625,0x4e8720,"LOOP1 @0x4e8625")
# second around 0x4e89cd (call 0x47fd10)
dump(0x4e89cd,0x4e8ad0,"LOOP2 @0x4e89cd")
