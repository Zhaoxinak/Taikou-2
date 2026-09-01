# -*- coding: utf-8 -*-
"""扫全镜像对 S15 (0x5203c0..0x5203db, 25B) 的所有引用，区分读/写，定位 setter。"""
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

import os, struct, bisect, pickle, collections
from capstone import *
from capstone.x86 import *

HERE = os.path.dirname(os.path.abspath(__file__))
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

S15 = 0x5203C0
S15END = 0x5203DB

_d = pickle.load(open(os.path.join(HERE, "_insn_addrs.pkl"), "rb"))
IMAP = _d[0]
FSTART = sorted(_d[1])
RVAS = sorted(IMAP)


def owner(va):
    r = va - BASE
    i = bisect.bisect_right(FSTART, r) - 1
    return (FSTART[i] + BASE) if i >= 0 else 0


def fend(va):
    r = va - BASE
    i = bisect.bisect_right(FSTART, r) - 1
    return (FSTART[i + 1] + BASE) if i + 1 < len(FSTART) else max(IMAP) + BASE + 1


hits = collections.defaultdict(list)
for rva in RVAS:
    off = rva
    va = rva + BASE
    ins = list(md.disasm(MEM[off:off + 12], va))
    if not ins:
        continue
    it = ins[0]
    for o in it.operands:
        txt = None
        if o.type == X86_OP_MEM:
            if o.mem.base == 0 and o.mem.index == 0 and o.mem.disp:
                a = o.mem.disp & 0xFFFFFFFF
                if S15 <= a <= S15END:
                    txt = ("abs", a, it.mnemonic, it.op_str)
        elif o.type == X86_OP_IMM:
            a = o.imm & 0xFFFFFFFF
            if S15 <= a <= S15END:
                txt = ("imm", a, it.mnemonic, it.op_str)
        if txt:
            wr = it.mnemonic in ("mov", "or", "and", "xor", "add", "sub",
                                 "inc", "dec", "shl", "shr", "not", "neg",
                                 "movzx", "movsx", "lea", "bts", "btr", "stos")
            # 只看写：目标操作数是内存
            is_write = False
            if it.mnemonic not in ("cmp", "test", "push", "lea", "movzx", "movsx") and \
               it.operands and it.operands[0].type == X86_OP_MEM:
                is_write = True
            if it.mnemonic in ("stosb", "stosd", "movs"):
                is_write = True
            hits[(txt[0], txt[1])].append((va, it.mnemonic, it.op_str, is_write, owner(va)))

print("== S15 引用汇总（按地址）==")
for (kind, a) in sorted(hits.keys()):
    sub = hits[(kind, a)]
    nw = sum(1 for x in sub if x[3])
    print(f"  [{kind}] 0x{a:06x} (S15+{a-S15})  {len(sub)} 处, 写 {nw}")

print("\n== 写入点明细 ==")
for (kind, a) in sorted(hits.keys()):
    sub = [x for x in hits[(kind, a)] if x[3]]
    if not sub:
        continue
    print(f"\n-- 0x{a:06x} (S15+{a-S15}) 写 {len(sub)} 处")
    for va, mn, ops, w, fn in sub:
        print(f"    0x{va:06x}  {mn:<7s} {ops:<34s} fn=0x{fn:06x}")

print("\n== 立即数引用 S15 基址（用于 mov ecx,0x5203c0 / add reg,0x5203c0）==")
for (kind, a) in sorted(hits.keys()):
    if kind != "imm":
        continue
    sub = hits[(kind, a)]
    c = collections.Counter((x[1], x[2]) for x in sub)
    print(f"\n-- 0x{a:06x}: {len(sub)} 处")
    for (mn, ops), n in c.most_common(20):
        print(f"     x{n:<3d} {mn:<7s} {ops}")
