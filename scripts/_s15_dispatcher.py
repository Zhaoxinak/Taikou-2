# -*- coding: utf-8 -*-
"""
从派发器 A(0x41a400)/B(0x41a660) 提取每个 bit 的检测/handler 关系：
对每个 get_a/get_b 调用提取其 bit 常量，并找紧随其后的 handler call（非访问器）。
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

import os, bisect, pickle, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

_d = pickle.load(open(os.path.join(HERE, "_insn_addrs.pkl"), "rb"))
FSTART = sorted(_d[1])
FSTART_VA = [x + BASE for x in FSTART]

GET_A = 0x49c390
GET_B = 0x49c3d0
ACCESSORS = {0x49c390, 0x49c3d0, 0x49c410, 0x49c420, 0x49c440,
             0x49c460, 0x49c4b0, 0x49c500, 0x49c520}


def push_imm_before(call_va, n=1, span=0x20):
    off = max(call_va - BASE - span, 0)
    ins = list(md.disasm(MEM[off:off + span + 8], BASE + off))
    pk = []
    for it in ins:
        if it.address >= call_va:
            break
        if it.mnemonic == "push":
            try:
                pk.append((it.address, int(it.op_str, 16) if it.op_str.startswith("0x") else int(it.op_str)))
            except ValueError:
                pk.append((it.address, None))
    return [p[1] for p in pk if p[0] < call_va][-n:]


def scan(va, length):
    off = va - BASE
    ins = list(md.disasm(MEM[off:off + length], va))
    print("\n===== 派发器 0x%06x (len 0x%x) =====" % (va, length))
    bit = None
    for it in ins:
        if it.mnemonic == "call":
            tgt = int(it.op_str, 16) if it.op_str.startswith("0x") else None
            if tgt in (GET_A, GET_B):
                b = push_imm_before(it.address, n=1)
                bit = b[0] if b else None
                kind = "A" if tgt == GET_A else "B"
                print("  0x%06x  get_%s(bit=%s)" % (it.address, kind, bit))
            elif tgt and tgt not in ACCESSORS and bit is not None:
                # 可能是 handler
                print("       -> handler call 0x%06x   (for bit=%s)" % (tgt, bit))
                bit = None  # 消费后重置，避免误配下一个 get
        elif it.mnemonic == "ret" or it.mnemonic == "retn":
            bit = None


if __name__ == "__main__":
    scan(0x41a400, 0x290)
    scan(0x41a660, 0x1a0)
