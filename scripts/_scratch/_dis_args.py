# -*- coding: utf-8 -*-
"""For each call site of given targets, dump the instruction window BEFORE the call
so we can read what (arg1,arg2) values are pushed / loaded."""
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

import sys, io, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *
BASE=0x400000
MEM=open(_ROOT + '/scripts/_unpacked_mem.bin','rb').read()
TEXT_START,TEXT_END=0x401000,0x4d0000
md=Cs(CS_ARCH_X86,CS_MODE_32)

def all_calls():
    out=[]; i=0
    while True:
        i=MEM.find(b'\xe8',i,TEXT_END-BASE)
        if i<0: break
        rel=struct.unpack_from('<i',MEM,i+1)[0]; t=(i+BASE)+5+rel
        if TEXT_START<=t<TEXT_END: out.append((i+BASE,t))
        i+=1
    return out
CALLS=all_calls()
targets=[int(a,0) for a in sys.argv[1:]]
for t in targets:
    sites=[s for s,tt in CALLS if tt==t]
    print(f'\n##### callers of {t:#x} ({len(sites)}) #####')
    for s in sites:
        start=max(TEXT_START,s-90)
        chunk=MEM[start-BASE:s+2-BASE]
        print(f'  --- call @{s:#08x} (host {None}) ---')
        for ins in md.disasm(chunk,start):
            if ins.address>s: break
            mark='>>>' if ins.address==s else '   '
            print(f'     {mark} {ins.address:#08x}  {ins.bytes.hex():<18s} {ins.mnemonic} {ins.op_str}')
