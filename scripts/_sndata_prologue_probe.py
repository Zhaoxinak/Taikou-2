# -*- coding: utf-8 -*-
r"""_sndata_prologue_probe.py -- 续225：确认各 leaf 的记录基址寄存器来源"""
import sys, os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _disasm_all import load_image, BASE
MEM = load_image()
md = Cs(CS_ARCH_X86, CS_MODE_32)

LEAVES = {
    "勢力図(0x4625a0)": 0x4625a0,
    "米市(0x461ed0)": 0x461ed0,
    "米市(0x4630c0)": 0x4630c0,
    "米市(0x4632e0)": 0x4632e0,
    "家中(0x462670)": 0x462670,
    "大名(0x462a80)": 0x462a80,
    "持有(0x462bc0)": 0x462bc0,
    "持有(0x462cf0)": 0x462cf0,
    "属下(0x462d40)": 0x462d40,
    "属下(0x462e10)": 0x462e10,
}

def va2off(va): return va - BASE
for name, va in LEAVES.items():
    off = va2off(va)
    print(f"\n=== {name} @0x{va:06x} 前 0x48 字节 ===")
    n=0
    for ins in md.disasm(MEM[off:off+0x48], va):
        print(f"0x{ins.address:06x}  {ins.bytes.hex():<18s} {ins.mnemonic:<7s} {ins.op_str}")
        n+=1
        if n>=18: break
