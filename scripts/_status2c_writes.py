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
# _status2c_writes.py — 全镜像找所有对 [reg+0x2c] 的【写】访问（byte/word，排除 esp基址）。
import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
CODE_LO, CODE_HI = 0x400000, 0x600000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
def off(va): return va - BASE

WR = {'mov','or','and','xor','add','sub','shl','shr','inc','dec','bts','btr','btc'}
TGT = 0x2c

def build_fn_bounds():
    fs = set(); i, n = 0, len(MEM)-5
    while i < n:
        b = MEM[i]
        if b==0xE8:
            rel=struct.unpack('<i',MEM[i+1:i+5])[0]; t=(BASE+i+5+rel)&0xffffffff
            if CODE_LO<=t<CODE_HI: fs.add(t)
        elif b in (0xC3,0xC2): fs.add(BASE+i+1)
        elif b==0xE9:
            rel=struct.unpack('<i',MEM[i+1:i+5])[0]; t=(BASE+i+5+rel)&0xffffffff
            if t>BASE+i and CODE_LO<=t<CODE_HI: fs.add(t)
        i+=1
    k=0
    while True:
        p=MEM.find(b'\x55\x89\xe5',k)
        if p<0: break
        fs.add(BASE+p); k=p+1
    fl=sorted(fs); nxt={}
    for i2 in range(len(fl)): nxt[fl[i2]]=fl[i2+1] if i2+1<len(fl) else fl[i2]+0x800
    return fl,nxt

def disasm_fn(va,nb):
    end=va+nb; cur=va; out=[]
    while cur<end:
        got=list(md.disasm(MEM[off(cur):off(end)],cur))
        if not got: cur+=1; continue
        for ins in got:
            if ins.address>=end: break
            out.append(ins)
        last=out[-1]; n2=last.address+last.size; cur=n2 if n2>cur else cur+1
    return out

def main():
    fl,fn_next=build_fn_bounds()
    writes=[]
    for fn in fl:
        nxt=fn_next[fn]
        if nxt-fn>0x800: nxt=fn+0x800
        for ins in disasm_fn(fn,nxt-fn):
            if ins.mnemonic not in WR: continue
            ops=ins.op_str
            if '0x2c]' not in ops: continue
            memop=None
            for o in ins.operands:
                if o.type==CS_OP_MEM and (o.mem.disp&0xfff)==TGT:
                    memop=o; break
            if memop is None: continue
            # 写：第一操作数是 mem
            if ins.operands and ins.operands[0].type==CS_OP_MEM:
                bname=md.reg_name(memop.mem.base) if memop.mem.base else None
                if bname=='esp': continue
                is_byte='byte ptr' in ops
                imm=None
                if len(ins.operands)>1 and ins.operands[1].type==CS_OP_IMM:
                    imm=ins.operands[1].imm&0xffffffff
                writes.append((ins.address,ins.mnemonic,ops,fn,is_byte,imm))
    # 去重（按地址）
    seen=set(); uniq=[]
    for w in writes:
        if w[0] in seen: continue
        seen.add(w[0]); uniq.append(w)
    print(f"全镜像 [reg+0x2c] 写访问（排除 esp）: {len(uniq)} 处")
    # 分组：byte 低字节写 / word 写
    byte_w=[w for w in uniq if w[4]]
    word_w=[w for w in uniq if not w[4]]
    print(f"\n=== byte[+0x2c] 写 : {len(byte_w)} ===")
    for (a,m,ops,fn,ib,imm) in sorted(byte_w):
        print(f"  0x{a:x}: {m} {ops}  fn=0x{fn:x}  imm={imm}")
    print(f"\n=== word[+0x2c] 写 : {len(word_w)} ===")
    for (a,m,ops,fn,ib,imm) in sorted(word_w):
        print(f"  0x{a:x}: {m} {ops}  fn=0x{fn:x}  imm={imm}")
    return 0

if __name__=='__main__':
    raise SystemExit(main())
