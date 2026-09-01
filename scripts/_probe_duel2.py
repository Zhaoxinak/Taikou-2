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

# 调度器：找 jmp/call [reg*4 + 0x4684c0] (modrm 85, disp c0 84 44 00)
print("==== dispatcher scan for 0x4684c0 ====")
i=0
while i+7 < len(MEM):
    if MEM[i]==0x85 and MEM[i+1]==0xc0 and MEM[i+2]==0x84 and MEM[i+3]==0x44 and MEM[i+4]==0x00:
        kind = "jmp" if MEM[i-1]==0xff and MEM[i-2]==0x24 else ("call" if MEM[i-1]==0xff and MEM[i-2]==0x14 else "?")
        print(f"  0x{BASE+i-2:08x}  {kind} [reg*4+0x4684c0]")
    i+=1

# 5 个 handler
for va in (0x468457,0x468489,0x468495,0x4684a0,0x4684a9):
    dump(va, 48, f"HANDLER {va:#08x}")

# 解析子函数（h3 调 0x467c80, h4 调 0x468000）
dump(0x467c80, 220, "SUB 0x467c80 (h3 callee)")
dump(0x468000, 220, "SUB 0x468000 (h4 callee)")
