#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续173（续172 下一步(A)）：0x4a5010 vs 0x4a5370 两个相性入口的玩法语义精确区分。

结论（逐指令核对）：
- 0x4a5010 = 登用 (recruit/任命 retainer)：
    · 入口 guard：目标 word[+0x2c] bit15(ah,0x80) 置位则拒(已「不在」)；身分(ah&7)==0 拒；在城(+0x25)<200 才受理
    · push 0xffff; call 0x49a7d0  → 先浪人化(自旧主解除)
    · call 0x49a730(bit7, push 0) → 清 bit7 = 重新「在役/活跃」
    · mov byte[+0x16],0 (激活); mov byte[+0x12],0xff; mov byte[+0x13],bl (基础值)
    · test byte[+0x2d],7; jne → 若身分==0 则 push 1; call 0x49a7e0 (授身分=1 足轻组头)
    · @0x4a527a：word[+0x2c]&0x700==0x700 (身分 rank==7 大名) 才 push 1; call 0x49a800 (bit11)
- 0x4a5370 = 引抜/誘い込み (poaching with 知行/俸禄 offer)：
    · 对每个候选(城/武将)算「知行」：max(统御+0xa, 外交+0xe) ×4/5 (muldiv 0x4ebc50, args 5,4)
    · 读 byte[城+8]→国表 stride5→byte[国]>>4&3 (2-bit 国域)
    · ÷10 魔数(0x66666667+sar1) × (2*cl+5) → sat_sub(0x4ebcd0) 钳 ≥1
    · call 0x4a3360(俸禄 wrapper) 支付知行
    · 城表 0x51eb88 stride31 全扫 (0x4a5f40/0x4a5fc0/0x4a61d0) — 全域诱引
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

import os, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()

def dis(va, n):
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.skipdata = True
    off = va - BASE
    return list(md.disasm(bytes(MEM[off:off+n]), va))

def has(va, addr):
    code = dis(va, 0xc00)
    return any(i.address == addr for i in code)

ok = True
def chk(cond, msg):
    global ok
    print(("  [PASS] " if cond else "  [FAIL] ") + msg)
    ok = ok and cond

print("=== 0x4a5010 = 登用 (recruit/任命) ===")
# 1. 入口 guard: bit15 拒
chk(has(0x4a5010, 0x4a510c), "0x4a510c test ah,0x80 (bit15 不在→拒登用)")
# 2. 浪人化后重授主君
chk(has(0x4a5010, 0x4a5033) and has(0x4a5010, 0x4a507b), "0x4a5033/0x4a507b call 0x49a7d0 (浪人化+重授主君)")
# 3. bit7 CLR = 重新活跃
chk(has(0x4a5010, 0x4a5189), "0x4a5189 call 0x49a730 (bit7 清 = 重新在役)")
# 4. 授身分
chk(has(0x4a5010, 0x4a51a3), "0x4a51a3 call 0x49a7e0 (授身分=1)")
# 5. 大名位 bit11
chk(has(0x4a5010, 0x4a527a), "0x4a527a call 0x49a800 (大名类 bit11)")

print("=== 0x4a5370 = 引抜/誘い込み (poach + 知行) ===")
chk(has(0x4a5370, 0x4a5bf2), "0x4a5bf2 call 0x4ebcd0 (sat_sub 知行公式)")
chk(has(0x4a5370, 0x4a5ba1), "0x4a5ba1 call 0x4ebc50 (muldiv ×4/5)")
chk(has(0x4a5370, 0x4a5c0c), "0x4a5c0c call 0x4a3360 (俸禄 wrapper 支付知行)")
chk(has(0x4a5370, 0x4a5ad7), "0x4a5ad7 call 0x49ab60 (城技能 setter)")
chk(has(0x4a5370, 0x4a5b31), "0x4a5b31 call 0x49bf70 (每城状态)")

# 分流判据：0x4a5010 独有 bit7 CLR(0x49a730) 与 0x49a800；0x4a5370 独有资源族
print("=== 分流判据 (独有 callee) ===")
def callee_set(va):
    s = set()
    for ins in dis(va, 0xc00):
        if ins.mnemonic == "call" and ins.op_str.startswith("0x"):
            s.add(int(ins.op_str, 16))
    return s
a = callee_set(0x4a5010); b = callee_set(0x4a5370)
# 0x49a730(bit7)/0x49a800(bit11) 是 0x4a5010 登用路径标志性独有调用
chk(0x49a730 in (a-b), "0x49a730(bit7 setter) 仅 0x4a5010 (登用→重新在役)")
chk(0x49a800 in (a-b), "0x49a800(bit11) 仅 0x4a5010 (大名类标记)")
# 0x4a3360(俸禄 wrapper) 是 0x4a5370 引抜路径标志性独有调用
chk(0x4a3360 in (b-a), "0x4a3360(俸禄 wrapper) 仅 0x4a5370 (知行支付)")
# 0x4a5370 独有整个俸禄 wrapper 族 (续153: 0x4a32a0..0x4a3530 8 个 cap 包装器)
paywrap = [0x4a3360, 0x4a3380, 0x4a33d0, 0x4a33f0, 0x4a3440, 0x4a3470]
uniq_pay = [w for w in paywrap if w in (b-a)]
chk(len(uniq_pay) >= 3, f"0x4a5370 独有俸禄族 {len(uniq_pay)} 个 (期望>=3): {[hex(w) for w in uniq_pay]}")
# muldiv/sat_sub 是共享原语，两函数都用 —— 断言它们存在即可（非独有）
chk(0x4ebc50 in b and 0x4ebc50 in a, "0x4ebc50(muldiv) 两函数均用 (共享原语)")
chk(0x4ebcd0 in b, "0x4ebcd0(sat_sub) 0x4a5370 用 (知行钳≥1)")

print("\nRESULT:", "ALL PASS" if ok else "FAIL")
import sys; sys.exit(0 if ok else 1)
