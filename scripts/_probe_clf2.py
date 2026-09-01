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
# 正确分类 0x516638 的所有引用：load / store / test / 寄存器间接写
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', "rb").read()
BASE = 0x400000
N = len(MEM)
cs = Cs(CS_ARCH_X86, CS_MODE_32)
cs.detail = True

STORE_MN = {"mov","or","and","add","sub","xor","inc","dec","not","shl","shr","xchg"}
LOAD_MN  = {"mov","lea","push"}
TARGET = "0x516638"

loads=[]; stores=[]; tests=[]; regind=[]; calls=[]
off=0
while off+1 < N:
    md = cs.disasm(MEM[off:off+16], BASE+off)
    did=False
    for ins in md:
        did=True
        s=ins.mnemonic; t=ins.op_str
        if TARGET in t:
            # 区分：第一个操作数是否是内存且含 TARGET（即写目标/读源）
            first = t.split(",")[0].strip() if "," in t else t.strip()
            is_memref = ("ptr" in first) and (TARGET in first)
            if s in STORE_MN and is_memref and first.endswith("]"):
                stores.append(ins)
            elif s=="test" and is_memref:
                tests.append(ins)
            elif s in LOAD_MN and ("0x516638" in t) and (TARGET in t.split(",")[-1]):
                # mov reg, 0x516638  (load 地址)
                if "ptr" not in t:
                    loads.append(ins)
            else:
                # 寄存器间接形式：如 [ecx + 0x516638]
                regind.append(ins)
        if s=="call" and ins.op_str.strip()=="0x4e87e0":
            calls.append(ins)
        off += ins.size
        break
    if not did:
        off += 1

def show(title, lst):
    print(f"\n==== {title}: {len(lst)} ====")
    for ins in lst:
        print(f"  {ins.address:#010x}  {ins.mnemonic} {ins.op_str}")

show("[LOAD] mov reg,0x516638", loads)
show("[STORE] 写 0x516638 (绝对)", stores)
show("[REGIND] 含 0x516638 的其它形式(含间接写)", regind)
show("[CALL] call 0x4e87e0", calls)
