# -*- coding: utf-8 -*-
"""
_modeflag_callsites.py — 探索：7 个模式标志 setter 的全部 call-site + 上下文反汇编
命名语义来自「谁在什么战斗阶段写它」。setter 集合（续186）：
  mode_m1_set  0x42c140 -> 0x511bf8
  mode_m2_a    0x43cb20 -> 0x51352c
  mode_m2_b    0x43cfc0 -> 0x51352c (xor 1)
  parity_a     0x43ca70 -> 0x513540
  parity_b     0x43ca90 -> 0x513540
  battle_type  0x43ca20 -> 0x513548
  handle_stat  0x43cb70 -> 0x513534
方法：E8 rel32 扫描算 target；命中后做「正确边界向后反汇编」抓 push 实参 + 战斗相位上下文。
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

import os, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
MEM = os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin')
BASE = 0x400000

SETTERS = {
    0x42c140: ("mode_m1_set", "0x511bf8"),
    0x43cb20: ("mode_m2_a", "0x51352c"),
    0x43cfc0: ("mode_m2_b_xor", "0x51352c"),
    0x43ca70: ("parity_a", "0x513540"),
    0x43ca90: ("parity_b", "0x513540"),
    0x43ca20: ("battle_type", "0x513548"),
    0x43cb70: ("handle_stat", "0x513534"),
}


def load():
    return open(MEM, "rb").read()


def find_calls(b, target):
    """返回所有 call target 的 VA 列表（E8 rel32）。"""
    out = []
    n = len(b)
    i = 0
    while i < n - 4:
        if b[i] == 0xE8:
            rel = struct.unpack_from("<i", b, i + 1)[0]
            next_ip = (i + BASE) + 5
            tgt = next_ip + rel
            if tgt == target:
                out.append(i + BASE)
        i += 1
    return out


def disasm_block(b, start_va, count):
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False
    off = start_va - BASE
    if off < 0:
        return []
    try:
        return list(md.disasm(b[off: off + count * 12 + 32], start_va))
    except Exception:
        return []


def backward_aligned(b, va, max_back=0x60):
    """找 va 之前最近的指令边界，反汇编到 va（含）返回指令列表。"""
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False
    for delta in range(1, max_back):
        start_va = va - delta
        if start_va - BASE < 0:
            break
        try:
            insns = list(md.disasm(b[start_va - BASE: start_va - BASE + 0x300], start_va))
        except Exception:
            continue
        # 是否有指令正好落在 va
        if any(x.address == va for x in insns):
            return insns
    return []


def main():
    b = load()
    for st_va, (name, gaddr) in SETTERS.items():
        print(f"\n########## {name} -> {gaddr} (setter 0x{st_va:x}) ##########")
        sites = find_calls(b, st_va)
        print(f"  call-site 数 = {len(sites)}")
        for sva in sites:
            insns = backward_aligned(b, sva, max_back=0x80)
            # 截取到 sva 前后窗口
            idx = next((k for k, x in enumerate(insns) if x.address == sva), None)
            if idx is None:
                continue
            lo = max(0, idx - 8)
            hi = min(len(insns), idx + 6)
            print(f"\n  --- call-site VA=0x{sva:x} ---")
            for x in insns[lo:hi]:
                mark = " <<<CALL" if x.address == sva else ""
                print(f"    0x{x.address:06x}  {x.mnemonic:7s} {x.op_str}{mark}")


if __name__ == "__main__":
    main()
