"""Enumerate field offsets in castle table 0x51eb88 (stride 31).
Linearly disassemble the image, collect every instruction that anchors a
register to the table base, then walk forward in the same routine collecting
[anchored + disp] memory accesses (disp in [0, STRIDE+3]) with width.
"""
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

import collections
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import (X86_REG_EAX, X86_REG_EBX, X86_REG_ECX, X86_REG_EDX,
                          X86_REG_ESI, X86_REG_EDI, X86_REG_EBP)

MEM = open(_ROOT + '/scripts/_unpacked_mem.bin','rb').read()
BASE = 0x400000
SZ = len(MEM)
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

TARGET = 0x51eb88
STRIDE = 31
REGNAMES = {X86_REG_EAX:'eax',X86_REG_EBX:'ebx',X86_REG_ECX:'ecx',X86_REG_EDX:'edx',
            X86_REG_ESI:'esi',X86_REG_EDI:'edi',X86_REG_EBP:'ebp'}

def regname(r):
    return REGNAMES.get(r)

# Pass 1: linear disasm, find base-loads
loads = []  # (va, dst_reg_name, kind)
code = MEM
addr = BASE
while addr < BASE + SZ:
    try:
        ins = next(md.disasm(code[addr-BASE:addr-BASE+16], addr))
    except StopIteration:
        addr += 1
        continue
    except Exception:
        addr += 1
        continue
    s = ins.mnemonic + ' ' + ins.op_str
    if '0x%x' % TARGET in s:
        if ins.mnemonic in ('add','mov') and len(ins.operands) == 2:
            dst = ins.operands[0]
            if dst.type == 1 and regname(dst.reg):
                loads.append((addr, regname(dst.reg), ins.mnemonic))
        elif ins.mnemonic == 'lea' and len(ins.operands) == 2:
            dst = ins.operands[0]
            if dst.type == 1 and regname(dst.reg):
                loads.append((addr, regname(dst.reg), 'lea'))
    addr = ins.address + ins.size

# Pass 2: walk forward
candidates = collections.defaultdict(lambda: collections.Counter())  # (disp,width)->Counter(va)
for va, dst, kind in loads:
    anchored = {dst}
    end = min(va + 600, BASE + SZ - 16)
    try:
        rows = list(md.disasm(MEM[va-BASE:end-BASE], va))
    except Exception:
        continue
    for ins in rows:
        s = ins.mnemonic + ' ' + ins.op_str
        # re-anchor if reg reassigned to base
        if ins.mnemonic in ('add','mov') and '0x%x'%TARGET in s and len(ins.operands)==2:
            d = ins.operands[0]
            if d.type==1 and regname(d.reg): anchored.add(regname(d.reg))
        if ins.mnemonic=='lea' and '0x%x'%TARGET in s and len(ins.operands)==2:
            d = ins.operands[0]
            if d.type==1 and regname(d.reg): anchored.add(regname(d.reg))
        for o in ins.operands:
            if o.type == 3:
                if regname(o.mem.base) in anchored:
                    disp = o.mem.disp
                    if 0 <= disp <= STRIDE + 3:
                        w = 4
                        if 'byte ' in s: w = 1
                        elif 'word ' in s: w = 2
                        elif 'dword ' in s: w = 4
                        candidates[(disp,w)][ins.address] += 1

print("=== field offset candidates (disp, width) -> #access sites ===")
for (disp,width),vas in sorted(candidates.items()):
    print("  +0x%02x (%2d)  w=%d   sites=%d   sample_va=%08x" % (disp, disp, width, len(vas), next(iter(vas))))
print("\ntotal base-load instructions:", len(loads))
