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
# _status2c_callers.py — 对每个 +0x2c 低字节 bit setter，找调用点并抽取 push 的 flag 实参。
import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
CODE_LO, CODE_HI = 0x400000, 0x600000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
def off(va): return va - BASE

SETTERS = {
    0x43dc40: 0x01, 0x43dc60: 0x02, 0x43dc80: 0x04, 0x43dca0: 0x08,
    0x43dcc0: 0x10, 0x43dce0: 0x20, 0x43dd00: 0x40, 0x43dd20: 0x80,
}

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
    nxt = {}
    for i2 in range(len(fl)):
        nxt[fl[i2]] = fl[i2+1] if i2+1 < len(fl) else fl[i2] + 0x800
    return fl, nxt

def disasm_range(va, n):
    out = []
    cur = va
    end = va + n
    while cur < end:
        chunk = MEM[off(cur):off(end)]
        got = list(md.disasm(chunk, cur))
        if not got: cur += 1; continue
        for ins in got:
            if ins.address >= end: break
            out.append(ins)
        last = out[-1]; n2 = last.address + last.size
        cur = n2 if n2 > cur else cur + 1
    return out

def main():
    fl, fn_next = build_fn_bounds()
    callers = {s: [] for s in SETTERS}
    # 找所有 call rel32 -> setter
    i, n = 0, len(MEM) - 5
    while i < n:
        if MEM[i] == 0xE8:
            rel = struct.unpack('<i', MEM[i+1:i+5])[0]
            t = (BASE + i + 5 + rel) & 0xffffffff
            if t in SETTERS:
                callers[t].append(BASE + i)
        i += 1
    for s in SETTERS:
        print(f"\n######## setter 0x{s:x} (bit{SETTERS[s].bit_length()-1}=0x{SETTERS[s]:x}) : {len(callers[s])} callers ########")
        flagvals = {}
        for ca in sorted(callers[s]):
            # 找所在函数
            fn = max([f for f in fl if f <= ca])
            nxt = fn_next[fn]
            if nxt - fn > 0x800: nxt = fn + 0x800
            insns = disasm_range(fn, nxt - fn)
            # 在调用点前回溯 push imm
            flag = None; push_src = None
            for idx, ins in enumerate(insns):
                if ins.address == ca:
                    # 向前找 push imm（0x68）或 0x6a（push imm8），取调用前最后一个
                    j = idx - 1
                    while j >= 0:
                        pi = insns[j]
                        if pi.mnemonic == 'push' and len(pi.operands) == 1 and pi.operands[0].type == CS_OP_IMM:
                            flag = pi.operands[0].imm & 0xffffffff
                            push_src = pi.address
                            break
                        if pi.mnemonic == 'call' or pi.mnemonic == 'ret':
                            break
                        j -= 1
                    break
            tag = ('flag=%d' % flag) if flag is not None else 'flag=REG/unknown'
            flagvals[flag] = flagvals.get(flag, 0) + 1
            print(f"  0x{ca:x}: fn=0x{fn:x}  {tag}")
        if len(flagvals) <= 6:
            print(f"  -> flag 取值分布: {dict(sorted(flagvals.items(), key=lambda x:(x[0] is None,x[0])))}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
