# -*- coding: utf-8 -*-
"""BSDATA 访问器 0x47d890 反汇编 + 调用方 + 0x4b5620。"""
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

import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
mem = open(MEM_PATH, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def off(va):
    return va - BASE


def dis(va, n=90, stop_ret=True):
    """从 va 起线性反汇编 n 条, 遇 ret 停(可选)。"""
    o = off(va)
    out = []
    for ins in md.disasm(mem[o:o + 4000], va):
        out.append((ins.address, ins.mnemonic, ins.op_str))
        if stop_ret and ins.mnemonic == "ret":
            break
        if len(out) >= n:
            break
    return out


def dump(va, n=90, title=""):
    print(f"\n===== {title or hex(va)} =====")
    for a, m, o in dis(va, n):
        print(f"  {a:08x}  {m:<8} {o}")


def e8_callers(target):
    """全镜像扫 call rel32 (e8) 指向 target。"""
    hits = []
    for i in range(len(mem) - 5):
        if mem[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", mem, i + 1)[0]
        dst = (BASE + i + 5 + rel) & 0xFFFFFFFF
        if dst == target:
            hits.append(BASE + i)
    return hits


def caller_ctx(addr, back=14):
    """取调用点前后指令(向上反汇编近似: 用有界线性扫描)"""
    o = off(addr)
    start = max(0, o - 90)
    seq = []
    for ins in md.disasm(mem[start:o + 8], BASE + start):
        seq.append((ins.address, ins.mnemonic, ins.op_str, ins.size))
    # 截到目标地址之后的 3 条
    idx = next((k for k, s in enumerate(seq) if s[0] == addr), None)
    if idx is None:
        return seq[-back - 3:]
    return seq[max(0, idx - back):idx + 4]


if __name__ == "__main__":
    for va in (0x47D890, 0x4B5620):
        dump(va, 90, f"{va:#x}")

    print("\n\n===== 0x47d890 的 e8 调用方 =====")
    c = e8_callers(0x47D890)
    print(f"共 {len(c)} 处")
    for a in c[:40]:
        print(f"\n  --- call @ {a:08x} (上下文) ---")
        for ad, m, o, sz in caller_ctx(a, 12):
            mark = " <<<" if ad == a else ""
            print(f"    {ad:08x}  {m:<8} {o}{mark}")

    print("\n\n===== 0x4b5620 的 e8 调用方 =====")
    c2 = e8_callers(0x4B5620)
    print(f"共 {len(c2)} 处")
    for a in c2[:20]:
        print(f"  call @ {a:08x}")
