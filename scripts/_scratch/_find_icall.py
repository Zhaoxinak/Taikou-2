# -*- coding: utf-8 -*-
"""穷举找「间接调用/读取」表: call/jmp/mov  [imm32 + reg*4] 形式。"""
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

import struct, json, bisect
from capstone import *
BASE=0x400000
mem=open(_ROOT + '/scripts/_unpacked_mem.bin','rb').read()
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=False
TLO,THI=0x401000,0x4f4000
targets=set(); i=0
while True:
    i=mem.find(b'\xe8',i)
    if i<0: break
    rel=struct.unpack_from('<i',mem,i+1)[0]
    t=(i+BASE)+5+rel
    if TLO<=t<THI: targets.add(t)
    i+=1
funcs=sorted(targets)
def host(va):
    k=bisect.bisect_right(funcs,va)-1
    return funcs[k] if k>=0 else 0

hits={}
end=0x4f4000-BASE
for off in range(0,min(len(mem),end)):
    if mem[off]!=0xff: continue
    if mem[off+1] not in (0x14,0x94,0x54,0xd4,0x24,0xa4,0x64,0xe4,0x34,0xb4,0x74,0xf4): continue
    for ins in md.disasm(mem[off:off+10], BASE+off):
        op=ins.op_str
        if '*4' in op and '0x' in op and '[' in op:
            try:
                imm=int(op.split('+')[1].strip().rstrip(']'),16)
            except Exception:
                break
            if not (0x4f0000<=imm<0x530000): break
            # 表长
            n=0
            while n<600:
                v=struct.unpack_from('<I',mem,imm-BASE+4*n)[0]
                if TLO<=v<THI: n+=1
                else: break
            if n>=4:
                key=(imm,n)
                hits.setdefault(key,[]).append((BASE+off, ins.mnemonic+' '+op, host(BASE+off)))
            break
rows=sorted(hits.items(), key=lambda kv:-kv[0][1])
print(f'间接表引用 {sum(len(v) for v in hits.values())} 处 / 表 {len(hits)} 张\n')
out=[]
for (imm,n),sites in rows:
    out.append({'table':hex(imm),'n':n,'sites':[{'at':hex(a),'ins':i,'func':hex(f)} for a,i,f in sites]})
    print(f'table {imm:#08x} n={n:3d}  sites={len(sites)}')
    for a,i,f in sites[:6]:
        print(f'    {a:#x} (func {f:#x})  {i}')
json.dump(out, open('_icall_tables.json','w',encoding='utf-8'), indent=1, ensure_ascii=False)
