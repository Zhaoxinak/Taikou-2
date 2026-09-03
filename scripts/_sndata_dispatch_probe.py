# -*- coding: utf-8 -*-
r"""_sndata_dispatch_probe.py -- 续225：钉死 idx->类名->handler 真实映射
读 0x4624f0 派发循环 + 跳转表 0x462584(6 dword) + 6 thunk + 名表 0x504938。
"""
import sys, os, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _disasm_all import load_image, BASE
MEM = load_image()
md = Cs(CS_ARCH_X86, CS_MODE_32)

def va2off(va): return va - BASE
def dis(va, n=0x60):
    off = va2off(va)
    out=[]
    for ins in md.disasm(MEM[off:off+n], va):
        out.append(ins)
    return out
def rd(va, n): return MEM[va2off(va):va2off(va)+n]
def rd_dwords(va, k):
    return struct.unpack("<%dI"%k, rd(va, 4*k))

print("===== 0x4624f0 派发循环（前 0xc0 字节）=====")
for ins in dis(0x4624f0, 0xc0):
    print(f"0x{ins.address:06x}  {ins.bytes.hex():<18s} {ins.mnemonic:<7s} {ins.op_str}")

print("\n===== 跳转表 0x462584 (6 dword) =====")
jt = rd_dwords(0x462584, 6)
for i,v in enumerate(jt):
    print(f"  idx{i} -> 0x{v:06x}")

print("\n===== 6 个 thunk 反汇编（各 0x50 字节）=====")
for i,v in enumerate(jt):
    print(f"\n--- thunk idx{i} @0x{v:06x} ---")
    for ins in dis(v, 0x50):
        tag = "   ; call" if ins.mnemonic=="call" and ins.op_str.startswith("0x") else ""
        print(f"0x{ins.address:06x}  {ins.bytes.hex():<18s} {ins.mnemonic:<7s} {ins.op_str}{tag}")

print("\n===== 名表 0x504938 (6x9B GBK) =====")
for i in range(6):
    b = rd(0x504938 + i*9, 9)
    try:
        s = b.rstrip(b"\x00").decode("gbk")
    except Exception:
        s = repr(b)
    print(f"  idx{i}: {b.hex()}  ->  '{s}'")
