
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

def dword_scan(target):
    b = struct.pack("<I", target)
    res = []
    s = 0
    while True:
        i = MEM.find(b, s)
        if i < 0:
            break
        res.append(i + BASE)
        s = i + 1
    return res

# 1) Whole-image control-flow scan to the 4 writers (any cflow op with absolute target)
WRITERS = {0x469480, 0x46947a, 0x4694a0, 0x4694e0, 0x469530,
           0x4694aa, 0x46950c, 0x469547}
CFLOW = {"call","jmp","je","jne","jb","jbe","ja","jae","jg","jge","jl","jle",
         "js","jns","jo","jno","jp","jnp","jcxz","jecxz","loop","loope","loopne"}
HEX = re.compile(r"^0x([0-9a-fA-F]+)$")
print("="*72)
print("WHOLE-IMAGE cflow to writers")
print("="*72)
hits = []
for ins in md.disasm(MEM, BASE):
    if ins.mnemonic in CFLOW:
        m = HEX.match(ins.op_str.strip())
        if m and (int(m.group(1),16) & 0xffffffff) in WRITERS:
            hits.append(ins)
            print(f"  {ins.address:#010x}: {ins.mnemonic} {ins.op_str}")
if not hits:
    print("  (none)")

# 2) Where are the special submenu callback 0x468250 / name tbl 0x504fb8 referenced?
print("\n" + "="*72)
print("dword refs to special-submenu anchors (0x468250, 0x504fb8, 0x4682f0, 0x504ff8)")
print("="*72)
for t, name in [(0x468250,"cb_special"),(0x504fb8,"name_special"),
                (0x4682f0,"cb_main"),(0x504ff8,"name_main")]:
    refs = dword_scan(t)
    print(f"\n  {name} {t:#010x}: {len(refs)} refs -> {[hex(r) for r in refs[:20]]}")
