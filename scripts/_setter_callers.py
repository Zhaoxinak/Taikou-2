# -*- coding: utf-8 -*-
"""_setter_callers.py — 找出对某组 setter 地址的全部 call 调用点，并反汇编调用点前 ~0x40 字节，
以观察传入的 flag 参数与调用上下文（this=ecx, [esp+4]=flag）。
用法: python scripts/_setter_callers.py <addr1> <addr2> ...
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

SETTERS = [int(x, 16) for x in sys.argv[1:]]
BIT = {0x49a880: 0, 0x49a8a0: 1, 0x49a8c0: 2, 0x49a8e0: 3}

def build_fn_bounds():
    fn_starts = set()
    i, n = 0, len(MEM) - 5
    while i < n:
        b = MEM[i]
        if b == 0xE8:
            rel = struct.unpack('<i', MEM[i+1:i+5])[0]
            t = (BASE + i + 5 + rel) & 0xffffffff
            if CODE_LO <= t < CODE_HI: fn_starts.add(t)
        elif b in (0xC3, 0xC2): fn_starts.add(BASE + i + 1)
        elif b == 0xE9:
            rel = struct.unpack('<i', MEM[i+1:i+5])[0]
            t = (BASE + i + 5 + rel) & 0xffffffff
            if t > BASE + i and CODE_LO <= t < CODE_HI: fn_starts.add(t)
        i += 1
    k = 0
    while True:
        p = MEM.find(b'\x55\x89\xe5', k)
        if p < 0: break
        fn_starts.add(BASE + p); k = p + 1
    fl = sorted(fn_starts)
    return fl

def disasm_range(va, n):
    return list(md.disasm(MEM[off(va):off(va)+n], va))

def main():
    fl = build_fn_bounds()
    callers = {s: [] for s in SETTERS}
    # 扫描所有 call rel32 目标
    i, n = 0, len(MEM) - 5
    while i < n:
        if MEM[i] == 0xE8:
            rel = struct.unpack('<i', MEM[i+1:i+5])[0]
            t = (BASE + i + 5 + rel) & 0xffffffff
            if t in SETTERS:
                callers[t].append(BASE + i)
        i += 1
    for s in SETTERS:
        print(f"\n######## setter 0x{s:x} (bit{BIT.get(s,'?')}) : {len(callers[s])} callers ########")
        for ca in sorted(callers[s]):
            print(f"\n  --- caller call-site 0x{ca:x} (fn 0x{fl and max([f for f in fl if f<=ca]):x})) ---")
            # 反汇编调用点前 0x50 字节
            start = ca - 0x50
            if start < BASE: start = BASE
            for ins in disasm_range(start, 0x60):
                mk = '  <<<CALL' if ins.address == ca else ''
                print(f"    0x{ins.address:x}: {ins.mnemonic} {ins.op_str}{mk}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
