# -*- coding: utf-8 -*-

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
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', "rb").read()
BASE=0x400000; cs=Cs(CS_ARCH_X86,CS_MODE_32); cs.detail=True
def dump(addr,bytes_,tag):
    print(f"\n==== {tag} @ {addr:#010x} ({bytes_}B) ====")
    off=addr-BASE
    for ins in cs.disasm(MEM[off:off+bytes_],addr):
        print(f"  {ins.address:#010x}  {ins.mnemonic} {ins.op_str}")

# 调度器：jmp/call [reg*4 + 0x4684c0] -> ff 24/14 85 c0 84 44 00
print("==== dispatcher scan (SIB form) ====")
i=0
while i+6 < len(MEM):
    if MEM[i] in (0x24,0x14) and MEM[i+1]==0x85 and MEM[i+2]==0xc0 and MEM[i+3]==0x84 and MEM[i+4]==0x44 and MEM[i+5]==0x00:
        kind = "jmp" if MEM[i-1]==0xff else ("call" if MEM[i-1]==0xff else "?")
        # find the ff
        j=i-1
        while j>=0 and MEM[j]!=0xff: j-=1
        print(f"  0x{BASE+j:08x}  ff {MEM[j+1]:02x} 85 c0 84 44 00  ({kind})")
    i+=1

# 其它 handler
dump(0x467970, 70, "H2 0x467970")
dump(0x468220, 70, "H0 0x468220")
dump(0x46aab0, 70, "H1 0x46aab0")
# 完整伤害公式
dump(0x467c80, 380, "SUB 0x467c80 FULL (击中要害 dmg)")
dump(0x468000, 380, "SUB 0x468000 FULL (一击必杀 dmg)")
# 修正 & 应用
dump(0x467a70, 130, "MOD 0x467a70")
dump(0x46b6e0, 90,  "APPLY 0x46b6e0")
