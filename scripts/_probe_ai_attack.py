
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

# ---- proper e8-caller scan: iterate all e8, resolve target ----
def find_callers(*targets):
    tset = set(targets)
    callers = {t: [] for t in targets}
    p = 0
    while p < SIZE:
        if MEM[p] == 0xe8:
            if p + 5 <= SIZE:
                r = struct.unpack("<i", MEM[p+1:p+5])[0]
                va_call = p + BASE
                tgt = (va_call + 5 + r) & 0xffffffff
                if tgt in tset:
                    callers[tgt].append(va_call)
            p += 5
        else:
            p += 1
    return callers

print("="*72)
print("e8 callers of key functions")
print("="*72)
for t, cs in find_callers(0x468290, 0x468340, 0x468860, 0x469310,
                           0x469480, 0x4694a0, 0x4694e0, 0x469530).items():
    print(f"  {t:#010x}: {[hex(c) for c in cs]}")

def dis(va, n=180):
    off = va - BASE
    out=[]; c=0
    for ins in md.disasm(MEM[off:off+0x900], va):
        out.append(f"{ins.address:#010x}: {ins.mnemonic} {ins.op_str}"); c+=1
        if c>=n: break
    return "\n".join(out)

print("\n" + "="*72)
print("0x468860 AI attack handler — full")
print("="*72)
print(dis(0x468860, 200))
