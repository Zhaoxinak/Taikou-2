# -*- coding: utf-8 -*-
"""_status2e_probe.py — 全镜像扫描实体表 +0x2e 状态字节的全部 读/写 访问，
按指令类型与立即数归类，辅助解码 1-byte 状态字的 bit 语义。
用法: python scripts/_status2e_probe.py
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
TGT = 0x2e  # 实体表内偏移

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

def imm_of(ins):
    for o in ins.operands:
        if o.type == CS_OP_IMM:
            return o.imm & 0xffffffff
    return None

def main():
    fl, fn_next = build_fn_bounds()
    writes = []   # (addr, fn, mnem, op_str, imm)
    reads = []
    for fn in fl:
        nxt = fn_next[fn]
        if nxt - fn > 0x800: nxt = fn + 0x800
        for ins in disasm_fn(fn, nxt - fn):
            for o in ins.operands:
                if (o.type == CS_OP_MEM and o.mem.base and o.mem.index == 0
                        and (o.mem.disp & 0xff) == TGT and o.mem.disp < 0x400):
                    m = ins.mnemonic
                    is_w = (m in WR_MNEM and ins.operands and ins.operands[0].type == CS_OP_MEM)
                    imm = imm_of(ins)
                    row = (ins.address, fn, m, ins.op_str, imm)
                    (writes if is_w else reads).append(row)
    print(f"=== +0x2e 写访问 : {len(writes)} 处 ===")
    for addr, fn, m, ops, imm in sorted(writes):
        print(f"  fn 0x{fn:x}  0x{addr:x}: {m} {ops}   imm={imm if imm is not None else '-'}")
    print(f"\n=== +0x2e 读访问 : {len(reads)} 处 ===")
    for addr, fn, m, ops, imm in sorted(reads):
        print(f"  fn 0x{fn:x}  0x{addr:x}: {m} {ops}   imm={imm if imm is not None else '-'}")
    # 按 bit 归类写立即数
    print("\n=== 写立即数 bit 归类 ===")
    from collections import Counter
    c = Counter()
    for addr, fn, m, ops, imm in writes:
        if imm is not None:
            c[imm] += 1
    for imm, cnt in sorted(c.items()):
        bits = [i for i in range(8) if imm & (1 << i)]
        print(f"  0x{imm:02x} ({imm:08b}) bits={bits} x{cnt}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
