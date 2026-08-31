# -*- coding: utf-8 -*-
"""_rank3_setters.py
1) 反汇编 +0x2d 打包/设置器 0x49a7e0，确认它的 (ptr, val) 约定与写入方式
2) 全镜像找所有 call 0x49a7e0 的调用点，并在调用点前反汇编，看传入的 val 常量
3) 顺便找其它 +0x2d 写者（+0x2c word 写、+0x2d 直接写），看是否带常量
"""
import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()
CODE_LO, CODE_HI = 0x400000, 0x600000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
def off(va): return va - BASE
def dis(va, n):
    return list(md.disasm(MEM[off(va):off(va)+n], va))

def calls_to(target):
    out = []
    i, n = 0, len(MEM) - 5
    while i < n:
        if MEM[i] == 0xE8:
            rel = struct.unpack('<i', MEM[i+1:i+5])[0]
            t = (BASE + i + 5 + rel) & 0xffffffff
            if t == target:
                out.append(BASE + i)
        i += 1
    return out

def main():
    print("=== 0x49a7e0 (+0x2d 打包器) ===")
    for ins in dis(0x49a7e0, 0x60):
        print(f"  0x{ins.address:x}: {ins.mnemonic} {ins.op_str}")
    print()

    SETTERS = [0x49a7e0, 0x49a7bf, 0x49a7d0, 0x49a808, 0x49a828, 0x49a840, 0x49a868]
    for s in SETTERS:
        cs = calls_to(s)
        print(f"=== call 0x{s:x} : {len(cs)} 处 ===")
        for c in cs[:40]:
            # 反汇编调用点前 12 条（看传入的 val）
            pre = dis(c - 0x60, 0x60)
            # 取靠近 call 的几条
            tail = [p for p in pre if p.address >= c-0x40]
            argnotes = []
            for p in tail:
                argnotes.append(f"0x{p.address:x}: {p.mnemonic} {p.op_str}")
            print(f"  -- 0x{c:x} --")
            for line in argnotes[-8:]:
                print("     " + line)
        print()
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
