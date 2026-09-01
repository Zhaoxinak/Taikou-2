# -*- coding: utf-8 -*-
"""找任命消息 id (0xe0 / 0xc92 / 0x159 / 0x621) 的消费者函数并反汇编。"""
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

import struct, os, bisect
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
mem = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

tg = set()
i = 0
while True:
    i = mem.find(b"\xe8", i)
    if i < 0:
        break
    rel = struct.unpack_from("<i", mem, i + 1)[0]
    t = (i + BASE) + 5 + rel
    if 0x401000 <= t < 0x4f0000:
        tg.add(t)
    i += 1
funcs = sorted(tg)
def host(va):
    k = bisect.bisect_right(funcs, va) - 1
    return funcs[k] if k >= 0 else 0

# 目标消息 id（全局）
targets = {0xe0: "M1#224 任命你为%s俸禄%u贯",
           0x159: "M1#345 任命你为队长俸禄10贯",
           0x621: "M1#1569 任命你为宿老",
           0xc92: "M2#578 任命%s为%s俸禄%u贯",
           0x4fd: "M2#1277 军功显著任命你为%s"}

# 找 push <imm> 等于 target 的 call 点
sites = []
for tgt in targets:
    # push imm32: 68 XX 00 00 00 ; push imm8: 6a XX
    for pat in (struct.pack("<BIB", 0x68, tgt, 0),):
        o = 0
        while True:
            o = mem.find(pat, o)
            if o < 0:
                break
            sites.append((BASE + o, tgt))
            o += 1
    # push imm8
    pat8 = struct.pack("<BB", 0x6a, tgt & 0xff)
    if tgt < 0x80:
        o = 0
        while True:
            o = mem.find(pat8, o)
            if o < 0:
                break
            sites.append((BASE + o, tgt))
            o += 1

out = [f"=== 任命消息引用 {len(sites)} 处 ==="]
byfn = {}
for va, tgt in sites:
    fn = host(va)
    byfn.setdefault(fn, []).append((va, tgt))

for fn in sorted(byfn):
    out.append(f"\nfunc {fn:#010x} : " + ", ".join(f"{hex(t)}" for _, t in byfn[fn][:6]))
    idx = funcs.index(fn)
    end = funcs[idx + 1] if idx + 1 < len(funcs) else fn + 0x300
    code = mem[fn - BASE: end - BASE]
    asm = list(md.disasm(code, fn))
    # 找 +0x2d 读/写 与 0x50d850 或 rank 计算
    for ins in asm:
        if "+0x2d" in ins.op_str or "0x2d" in ins.op_str or "0x50d850" in ins.op_str:
            out.append(f"   > {ins.address:#010x}  {ins.mnemonic} {ins.op_str}")
    out.append(f"   ({len(asm)} 条)")

open(os.path.join(HERE, "_appt.txt"), "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out[:140]))
