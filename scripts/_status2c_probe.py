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
# _status2c_probe.py — 在引用实体表 0x519868 的函数内，穷举偏移 +0x2c 的全部内存访问，
# 区分 byte ptr / word ptr，并抽取立即数，用于破解 +0x2c 低字节（bits 0-7）位域语义。
import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
CODE_LO, CODE_HI = 0x400000, 0x600000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
def off(va): return va - BASE

WR_MNEM = {'mov', 'add', 'sub', 'or', 'and', 'xor', 'inc', 'dec', 'shl', 'shr'}

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

def disasm_fn(va, max_bytes):
    end = va + max_bytes; cur = va; out = []
    while cur < end:
        chunk = MEM[off(cur):off(end)]
        got = list(md.disasm(chunk, cur))
        if not got: cur += 1; continue
        for ins in got:
            if ins.address >= end: break
            out.append(ins)
        last = out[-1]; nxt = last.address + last.size
        cur = nxt if nxt > cur else cur + 1
    return out

def main():
    tbl = 0x519868
    target = 0x2c
    fl, fn_next = build_fn_bounds()
    # 引用该基址的函数
    sites = set()
    for fn in fl:
        nxt = fn_next[fn]
        if nxt - fn > 0x800: nxt = fn + 0x800
        for ins in disasm_fn(fn, nxt - fn):
            for o in ins.operands:
                v = None
                if o.type == CS_OP_IMM: v = o.imm & 0xffffffff
                elif o.type == CS_OP_MEM and o.mem.disp: v = o.mem.disp & 0xffffffff
                if v == tbl:
                    sites.add(fn); break
            else:
                continue
            break
    print(f"表 {tbl:#x}: {len(sites)} 个函数引用; 扫描偏移 +0x{target:x}")
    byte_w = {}; byte_r = {}; word_w = {}; word_r = {}
    for fn in sorted(sites):
        nxt = fn_next[fn]
        if nxt - fn > 0x800: nxt = fn + 0x800
        for ins in disasm_fn(fn, nxt - fn):
            for o in ins.operands:
                if o.type == CS_OP_MEM and o.mem.base and o.mem.index == 0 and (o.mem.disp & 0xfff) == target:
                    is_byte = 'byte ptr' in ins.op_str
                    is_word = 'word ptr' in ins.op_str
                    m = ins.mnemonic
                    rw = None
                    if m in WR_MNEM and ins.operands and ins.operands[0].type == CS_OP_MEM:
                        # write if mem operand is dest
                        if 'byte ptr' in ins.op_str:
                            rw = 'BrW' if is_byte else ('WrW' if is_word else 'WrW')
                        else:
                            rw = 'WrW'
                    else:
                        rw = 'BrR' if is_byte else ('WrR' if is_word else 'R')
                    # 提取立即数（第二个操作数）
                    imm = None
                    if len(ins.operands) > 1 and ins.operands[1].type == CS_OP_IMM:
                        imm = ins.operands[1].imm & 0xffffffff
                    entry = (ins.address, m, ins.op_str, imm, fn)
                    if 'byte ptr' in ins.op_str:
                        (byte_w if rw.startswith('B') and rw.endswith('W') else byte_r).setdefault(ins.address, entry)
                    elif 'word ptr' in ins.op_str:
                        (word_w if rw.endswith('W') else word_r).setdefault(ins.address, entry)
                    else:
                        # 默认当 word
                        (word_w if rw.endswith('W') else word_r).setdefault(ins.address, entry)
    def show(d, title, want_imm=None):
        print(f"\n===== {title} : {len(d)} 处 =====")
        immset = {}
        for a,(addr,m,ops,imm,fn) in sorted(d.items()):
            tag = ''
            if imm is not None:
                immset[imm] = immset.get(imm,0)+1
            print(f"  0x{addr:x} [{m} {ops}] imm={imm} fn=0x{fn:x}")
        if immset:
            print(f"  -> 立即数集合: {sorted(immset.items(), key=lambda x:x[0])}")
    show(byte_w, "byte[+0x2c] WRITE")
    show(byte_r, "byte[+0x2c] READ")
    show(word_w, "word[+0x2c] WRITE")
    show(word_r, "word[+0x2c] READ")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
