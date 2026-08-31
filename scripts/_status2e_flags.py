# -*- coding: utf-8 -*-
"""_status2e_flags.py — 对每个 +0x2e bit setter 的全部 call 点，提取传入的 flag 参数
(紧邻 call 前的 push imm / push reg / mov [esp],reg)，统计常量 0/1 与变量调用。
同时反汇编 4 个动态掩码测试点，看 bl/dl 如何构造（是否就是 bit1/bit3）。
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

SETTERS = {0x49a880:0, 0x49a8a0:1, 0x49a8c0:2, 0x49a8e0:3}

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
    return sorted(fn_starts)

def disasm_range(va, n):
    return list(md.disasm(MEM[off(va):off(va)+n], va))

def get_flag_arg(ca):
    """call 前最近一条改写 [esp] 或 push 的指令。返回 (kind, val)。"""
    # 向前扫描最多 8 条指令
    cur = ca
    seen = []
    steps = 0
    while steps < 40 and cur >= BASE:
        # 逐条反汇编（单条）
        ins_l = disasm_range(cur - 0x20, 0x40)
        # 找 call 之前的指令序列
        break
    # 简单策略：反汇编 call 前 0x30 字节，找最后一条 push 或 mov [esp]
    pre = disasm_range(ca - 0x30, 0x30)
    last_push = None
    for ins in pre:
        if ins.address >= ca: break
        if ins.mnemonic == 'push':
            for o in ins.operands:
                if o.type == CS_OP_IMM:
                    last_push = ('imm', o.imm & 0xffffffff)
                else:
                    last_push = ('reg', ins.op_str)
        elif ins.mnemonic == 'mov' and ins.op_str.startswith('dword ptr [esp'):
            last_push = ('mov_esp', ins.op_str)
    return last_push

def main():
    fl = build_fn_bounds()
    callers = {s: [] for s in SETTERS}
    i, n = 0, len(MEM) - 5
    while i < n:
        if MEM[i] == 0xE8:
            rel = struct.unpack('<i', MEM[i+1:i+5])[0]
            t = (BASE + i + 5 + rel) & 0xffffffff
            if t in SETTERS:
                callers[t].append(BASE + i)
        i += 1
    for s in SETTERS:
        cnt = {0:0, 1:0, 'reg':0, 'other':0}
        examples = []
        for ca in sorted(callers[s]):
            fa = get_flag_arg(ca)
            if fa is None:
                cnt['other'] += 1
            elif fa[0] == 'imm':
                cnt[fa[1]] = cnt.get(fa[1], 0) + 1
                if len(examples) < 6 and fa[1] not in (0,1):
                    examples.append((ca, fa))
            else:
                cnt['reg'] += 1
                if len(examples) < 6:
                    examples.append((ca, fa))
        print(f"\nsetter 0x{s:x} bit{SETTERS[s]}: {len(callers[s])} callers  flag分布={cnt}")
        for ca, fa in examples:
            print(f"   非0/1 flag @0x{ca:x}: {fa}")

    # 动态掩码测试点
    dyn = [0x403902, 0x4b7874, 0x4b7f6c, 0x4b7f75]
    for d in dyn:
        print(f"\n=== 动态掩码测试点 0x{d:x} (反汇编前 0x40) ===")
        for ins in disasm_range(d - 0x40, 0x48):
            mk = '  <<<' if ins.address == d else ''
            print(f"  0x{ins.address:x}: {ins.mnemonic} {ins.op_str}{mk}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
