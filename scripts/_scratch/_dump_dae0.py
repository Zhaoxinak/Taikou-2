
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
def dump(start,size,label):
    print("==== %s @0x%x ===="%(label,start))
    n=0
    for ins in md.disasm(mem[start-base:start-base+size],start):
        print("%08x  %-9s %s"%(ins.address,ins.mnemonic,ins.op_str))
        n+=1
        if n>120: break
# dump a few sub-parsers
for f in (0x47dae0,0x47dce0,0x47e130):
    dump(f,0x280,"fn 0x%x"%f)
