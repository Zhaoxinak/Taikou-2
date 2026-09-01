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

# 调度器：跳表 0x4684c0 的 disp32 = c0 84 44 00，找前后字节
print("==== scan disp32 0x4684c0 (c0 84 44 00) ====")
i=0
while i+4 < len(MEM):
    if MEM[i]==0xc0 and MEM[i+1]==0x84 and MEM[i+2]==0x44 and MEM[i+3]==0x00:
        ctx = MEM[i-3:i+5]
        print(f"  0x{BASE+i-3:08x}  bytes: {ctx.hex()}")
    i+=1

dump(0x4680e0, 160, "一击必杀 0x468000 tail")
dump(0x467a70, 210, "MOD 0x467a70 (击中要害收尾修正)")
dump(0x46b6e0, 120, "APPLY 0x46b6e0 (伤害应用?)")
