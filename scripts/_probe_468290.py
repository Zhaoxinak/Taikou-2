
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
import struct, re
from capstone import *

MEM_PATH = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
with open(MEM_PATH, "rb") as f:
    MEM = f.read()
SIZE = len(MEM)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def dis(va, n=200):
    off = va - BASE
    out=[]; c=0
    for ins in md.disasm(MEM[off:off+0x900], va):
        out.append(f"{ins.address:#010x}: {ins.mnemonic} {ins.op_str}"); c+=1
        if c>=n: break
    return "\n".join(out)

print("="*72); print("0x468290 攻击判定 (action decision) — full"); print("="*72)
print(dis(0x468290, 130))

# find e8 callers of 0x468290
print("\n"+"="*72); print("e8 callers of 0x468290"); print("="*72)
b = struct.pack("<I", (0x468290 - BASE - 5) & 0xffffffff)
found=[]; s=0
while True:
    i = MEM.find(b, s)
    if i<0: break
    if MEM[i-1]==0xe8: found.append(i+BASE)
    s=i+1
print("  callers:", [hex(x) for x in found])
