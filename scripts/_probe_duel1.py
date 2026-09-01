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
import struct
def dump(addr,bytes_,tag):
    print(f"\n==== {tag} @ {addr:#010x} ({bytes_}B) ====")
    off=addr-BASE
    for ins in cs.disasm(MEM[off:off+bytes_],addr):
        print(f"  {ins.address:#010x}  {ins.mnemonic} {ins.op_str}")

# 跳表 0x4684c0：读 5 个 dword 目标
off=0x4684c0-BASE
print("==== JUMP TABLE 0x4684c0 (5 dwords) ====")
for i in range(5):
    t=struct.unpack_from("<I", MEM, off+i*4)[0]
    print(f"  [{i}] -> 0x{t:08x}")
# 攻击判定入口
dump(0x468290, 200, "ATTACK JUDGE 0x468290")
# 跳表 dispatcher 附近
dump(0x4684a0, 120, "around JUMPTABLE 0x4684c0")
