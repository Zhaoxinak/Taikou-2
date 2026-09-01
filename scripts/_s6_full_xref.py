"""S6 (0x516610, 46B) 字段访问全谱：对 46 个字节地址逐个做指令包含式 xref，
   抽取每条引用的函数、指令、读/写/位宽、cmp/test 立即数。"""
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

import struct, pickle
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_MEM, X86_REG_EBP

IMG = open(_ROOT + '/scripts/_unpacked_mem.bin','rb').read()
BASE = 0x400000
d, starts = pickle.load(open(_ROOT + '/scripts/_insn_addrs.pkl','rb'))   # d: va->(size,...) ; starts: sorted list
SIZE = {va: s[0] for va, s in d.items()}
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

def find_insn(fo):
    # fo: 文件偏移；返回包含它的指令起始（文件偏移）
    for j in range(max(0, fo-16), fo+1):
        if j in SIZE and j <= fo < j + SIZE[j]:
            return j
    return None

def func_of(fo):
    # 最近的前驱 call 目标 = 函数入口（启发式，starts 为文件偏移列表）
    best = None
    for s in starts:
        if s <= fo:
            if best is None or s > best:
                best = s
        else:
            break
    return best if best is not None else fo

def width_of(op_str, mnem):
    if 'byte ptr' in op_str: return 'B'
    if 'word ptr' in op_str: return 'W'
    if 'dword ptr' in op_str: return 'D'
    return '?'

def classify(mnem, op_str):
    if mnem.startswith('mov'):
        parts = op_str.split(',')
        dst, src = parts[0].strip(), parts[1].strip()
        if 'ptr' in dst and 'ptr' not in src:
            return 'W'
        if 'ptr' in src and 'ptr' not in dst:
            return 'R'
        return '?'
    if mnem in ('test','cmp','and','or','add','sub'):
        return 'T'
    return '?'

def refs_for(imm):
    pat = struct.pack('<I', imm)
    out = []
    off = 0
    while True:
        i = IMG.find(pat, off)   # i 是文件偏移
        if i < 0: break
        off = i + 1
        hit = find_insn(i)       # hit 是文件偏移（=VA-BASE）
        if hit is None: continue
        sz = SIZE[hit]
        b = list(md.disasm(IMG[hit:hit+sz+16], BASE + hit))
        if not b: continue
        ins = b[0]
        fn = func_of(hit)
        w = width_of(ins.op_str, ins.mnemonic)
        c = classify(ins.mnemonic, ins.op_str)
        out.append((BASE + hit, BASE + fn, f'{ins.mnemonic} {ins.op_str}', w, c))
    return out

import collections
print(f"{'off':>4} {'abs':>8} {'n':>4}")
TARGET = {0x14,0x16,0x18,0x1a,0x1e,0x20,0x22,0x24,0x26,0x28,0x29,0x2a,0x2c,0x0e,0x0f,0x12,0x13}
for off in range(0x2e):
    imm = 0x516610 + off
    refs = refs_for(imm)
    # 剔除 mov reg, 0x516610 这种取基址（仅当整条指令立即数恰好等于基址）
    refs = [r for r in refs if r[0] != 0x4a1fdd and imm != 0x516610]
    print(f"+{off:02x}  0x{imm:06x}  {len(refs):>4}")
    wc = collections.Counter(r[3] for r in refs)
    cc = collections.Counter(r[4] for r in refs)
    print(f"      widths={dict(wc)} dirs={dict(cc)}")
    if off in TARGET:
        for va, fn, txt, w, c in refs[:10]:
            print(f"      0x{va:06x} fn=0x{fn:06x} [{c}{w}] {txt}")
    for va, fn, txt, w, c in refs:
        if any(k in txt for k in ('cmp','test')):
            print(f"      [cmp/test] 0x{va:06x} fn=0x{fn:06x}  {txt}")
