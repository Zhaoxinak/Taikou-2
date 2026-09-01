
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
def disasm(s,e,label,out):
    out.append("==== %s (0x%x-0x%x) ===="%(label,s,e))
    for ins in md.disasm(mem[s-base:e-base],s):
        if ins.address>e: break
        out.append("%08x  %-9s %s"%(ins.address,ins.mnemonic,ins.op_str))
out=[]
disasm(0x47f340,0x47f740,"scene-block decoder 0x47f350 / reader 0x47f5c0",out)
disasm(0x47ff50,0x480100,"main record loop 0x47ff68",out)
open("_sndata_b.asm","w").write("\n".join(out))
print("ok lines",len(out))
