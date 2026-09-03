# -*- coding: utf-8 -*-
r"""续226 探针：对 6 类顾问咨询 leaf 全函数做 All-GP 偏移扫描（权威字段集来源）。
方法复用续225 T8（线性 disasm + skipdata + 任意 GP 基址 + disp<0x31 收集）。
本次用 disasm_func 界定函数边界，避免跨函数泄漏下一函数的记录读。
"""
import sys, os, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _disasm_all import load_image, BASE

MEM = load_image()
_RE = re.compile(r'\[(eax|ecx|edx|esi|edi|ebx|esp|ebp)(?:\s*\+\s*(0x[0-9a-f]+|[0-9]+))?\]')
_BRANCH = ('jmp','ja','jae','jb','jbe','je','jne','jg','jge','jl','jle',
           'jo','jno','js','jns','jp','jnp','jcxz','jecxz','loop','loope','loopne')
def va2off(va): return va - BASE
def rd(va, n): return MEM[va2off(va):va2off(va)+n]
def _imm(s): return int(s,16) if s.lower().startswith("0x") else int(s)
def disasm(va, n):
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.skipdata = True
    return list(md.disasm(rd(va, n), va))
def disasm_func(va, win=0x800):
    """界定本函数体：仅按 jmp/jcc 前向分支延伸 maxaddr（call 不延伸，避免把被调子函数的记录读泄漏进来）。
    越过 maxaddr+0x30 即停。"""
    insns = disasm(va, win)
    maxaddr = va + 0x200
    keep = []
    for ins in insns:
        if ins.address > maxaddr + 0x30: break
        keep.append(ins)
        if ins.mnemonic in _BRANCH and ins.op_str.startswith('0x'):
            t = _imm(ins.op_str)
            if t >= va:
                maxaddr = max(maxaddr, t)
    return keep

def allgp_offsets(va):
    offs=set()
    for ins in disasm_func(va, 0x600):
        for m in _RE.finditer(ins.op_str):
            disp = m.group(2)
            d = _imm(disp) if disp else 0
            if 0 <= d < 0x31: offs.add(d)
    return offs

# 6 类 leaf 集合（含 thunk→leaf 与 worker）
LEAVES = [
    ("T0_勢力図_leaf",        0x4625a0),
    ("T1_米市_default",       0x461ed0),
    ("T1_米市_sub_id2",       0x4630c0),
    ("T1_8_米市_sub6",        0x4632e0),
    ("T2_家中排行_leaf",      0x462670),
    ("T3_大名情報_leaf",      0x462a80),
    ("T4_持有_thunk",         0x462bc0),
    ("T4_持有_worker",        0x462cf0),
    ("T5_属下_thunk",         0x462d40),
    ("T5_属下_worker",        0x462e10),
]
if __name__ == "__main__":
    for name, va in LEAVES:
        offs = allgp_offsets(va)
        print(f"{name:22s} {hex(va)}  offs={sorted(hex(x) for x in offs)}")
