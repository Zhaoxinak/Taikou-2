"""追踪 getLo(0x439050) 全部调用点的参数装配，反推 a(9类)与 c(20属性)语义。"""
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

import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

data = open(_ROOT + '/scripts/_unpacked_mem.bin','rb').read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)

def calls_to(target):
    out=[]; n=len(data); pos=0
    while pos<n-5:
        if data[pos]==0xe8:
            rel=struct.unpack('<i',data[pos+1:pos+5])[0]
            dest=BASE+pos+5+rel
            if dest==target: out.append(BASE+pos)
        pos+=1
    return out

def disasm(start, length):
    chunk=data[(start-BASE):(start-BASE+length)]
    return list(md.disasm(chunk, start))

def track(regs, ins):
    if ins.mnemonic == 'mov':
        parts = [p.strip() for p in ins.op_str.split(',')]
        if len(parts)==2:
            dst, src = parts
            if dst in ('eax','ecx','edx','ebx','esi','edi','al','cl','ah','ch','ax','cx'):
                if src.startswith('0x'):
                    regs[dst]=('imm', int(src,16))
                elif src in regs:
                    regs[dst]=regs[src]
                else:
                    regs[dst]=('src', src)

def fmt(regval):
    if regval[0]=='imm': return 'imm=%d'%regval[1]
    if regval[0]=='src': return '<-%s'%regval[1]
    return '?'

def analyze(caller):
    start = max(BASE, caller - 110)
    insns = disasm(start, (caller - start) + 12)
    regs = {}
    window=[]
    last_call_idx=None
    for i,ins in enumerate(insns):
        track(regs, ins)
        window.append((ins.address, ins.mnemonic+' '+ins.op_str))
        if ins.address==caller:
            last_call_idx=i; break
    lo = max(0, last_call_idx-14)
    ctx = window[lo:last_call_idx+1]
    return ctx, fmt(regs.get('eax',('?','?'))), fmt(regs.get('ecx',('?','?')))

cs = calls_to(0x439050)
print("getLo callers:", len(cs))
for c in cs:
    ctx, ea_s, ec_s = analyze(c)
    print("\n=== caller 0x%08x : eax(a?)=%s  ecx(c?)=%s ==="%(c, ea_s, ec_s))
    for a,s in ctx:
        mark='>>' if a==c else '  '
        print("%s0x%08x  %s"%(mark,a,s))
