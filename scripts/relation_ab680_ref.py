# -*- coding: utf-8 -*-
"""relation_ab680_ref.py — 续185 破解 0x4ab680 成功分支「关系矩阵 ±delta 写点」

关键结论（emu + 反汇编双确认）：

0x4ab680（关系行动 dispatcher）成功分支的「关系变动量写点」= **0x49fe40（set_diplomacy）**，
它把两实体间关系矩阵记录的 **低 3 位 = 新关系级别 newrel = sat_sub(rel, 1) = rel-1**
（rel=当前级别=0x49fd60(a,b)，sat_sub 经 0x4ebcd0 实现；成功分支 rel 减 1）。

路径（反汇编实锤 0x4ab72f+）：
  rel   = 0x49fd60(a, b)            ; 当前关系值
  newrel= 0x4ebcd0(rel, 1)          ; = sat_sub(rel,1) = rel-1（"push 1" 经 add esp,8 残留为第 2 参）
  0x49fe40(a, b, newrel)            ; 经 0x49fd80 取矩阵记录指针
        byte[rec] = (byte[rec] & ~7) | (newrel & 7)   ; 低 3 位 = 新级别，高 5 位保留

即：这是**关系矩阵**（每对实体 7B 记录 @0x521aa8+idx*7）层面的写点，与
续184 的「国政治[prov].byte[0xc] 外交寄存器 +1」是**伴生双写、方向相反**：
  - 0x4ab680 成功 → 矩阵 low3 减 1（敌对/威嚇类行动使关系恶化）
  - 0x4ab3c0 成功 → 国政治[prov].byte[0xc] 等级 +1（進貢/友好类行动使外交等级提升）

另：成功分支还经 0x49b550 取目标城 idx、0x4a33f0 在城表 +0x12c 写外交标志（本脚本以 force 跳过其副作用）。

证据：本脚本三档 emu 自测（A 0x4ebcd0 公式 / B 0x49fe40 矩阵写 / C 0x4ab680 端到端）+ 静态断言。
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

import os
import sys
import struct
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESP, UC_X86_REG_ECX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EIP

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
IMG = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
STACK = 0x7F000
RET = 0x90000

FORCE = {}
FORCE_ARGC = {}
STOP = RET


def _uc():
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(BASE, len(IMG))
    uc.mem_write(BASE, IMG)
    uc.mem_map(STACK - 0x10000, 0x20000)
    uc.mem_map(RET, 0x1000)
    uc.mem_write(RET, b"\xc3")
    return uc


def _hook(uc, addr, size, ud):
    if addr == STOP:
        uc.emu_stop()
        return
    if addr in FORCE:
        e = uc.reg_read(UC_X86_REG_ESP)
        ret = int.from_bytes(uc.mem_read(e, 4), "little")
        uc.reg_write(UC_X86_REG_EAX, FORCE[addr] & 0xFFFFFFFF)
        n = FORCE_ARGC.get(addr, 0)
        uc.reg_write(UC_X86_REG_ESP, e + 4 + n * 4)
        uc.reg_write(UC_X86_REG_EIP, ret)


def _run(uc, func, ecx, argmap, forces, force_argc=None, stop=None):
    global FORCE, FORCE_ARGC, STOP
    FORCE = dict(forces)
    FORCE_ARGC = dict(force_argc or {})
    STOP = stop if stop is not None else RET
    try:
        uc.hook_del(_run._h)
    except Exception:
        pass
    _run._h = uc.hook_add(UC_HOOK_CODE, _hook)
    esp = STACK
    uc.mem_write(esp, RET.to_bytes(4, "little"))
    for off, v in argmap.items():
        uc.mem_write(esp + off, (v & 0xFFFFFFFF).to_bytes(4, "little"))
    uc.reg_write(UC_X86_REG_ESP, esp)
    if ecx is not None:
        uc.reg_write(UC_X86_REG_ECX, ecx & 0xFFFFFFFF)
    uc.emu_start(func, STOP)
    return uc.reg_read(UC_X86_REG_EAX) & 0xFFFFFFFF


def _t(name, cond):
    print("  [%s] %s" % ("OK" if cond else "NG", name))
    return bool(cond)


def sat_sub(a, b):
    a &= 0xFFFF
    b &= 0xFFFF
    return (a - b) if a > b else 0


# === A. 0x4ebcd0(a,b) = (a>b)?(a-b):0 直接验证 ===
def _ebcd0(a, b):
    uc = _uc()
    return _run(uc, 0x4ebcd0, None, {4: a, 8: b}, {})


# === B. 0x49fe40(a,b,N) 把矩阵记录低 3 位写成 N（高 5 位保留）===
def _fe40(a, b, N, init_byte):
    uc = _uc()
    rb = 0xC0000
    uc.mem_map(rb, 0x1000)
    uc.mem_write(rb, bytes([init_byte]))
    forces = {0x49fd80: rb}
    _run(uc, 0x49fe40, None, {4: a, 8: b, 0xC: N}, forces, {0x49fd80: 0})
    return uc.mem_read(rb, 1)[0]


# === C. 0x4ab680 成功分支端到端：矩阵 low3 = sat_sub(rel,1) ===
def _ab680_success(rel, init_byte):
    uc = _uc()
    rb = 0xC0000
    uc.mem_map(rb, 0x1000)
    uc.mem_write(rb, bytes([init_byte]))
    gov_a = 0xC1000
    gov_b = 0xC2000
    for g in (gov_a, gov_b):
        uc.mem_map(g, 0x1000)
        uc.mem_write(g + 4, b"\x00\x00")  # word[4]=lord 0（<370，门可过）
    uc.mem_write(STACK - 0x200, b"\x00" * 0x300)
    uc.reg_write(UC_X86_REG_ESP, STACK)
    uc.reg_write(UC_X86_REG_ESI, gov_a)
    uc.reg_write(UC_X86_REG_EDI, gov_b)
    forces = {0x49fd60: rel, 0x49fd80: rb, 0x49b550: 0, 0x4a33f0: 0}
    # 从成功分支起点 0x4ab72f 跑到 0x4ab77e（mov ax,1 前），STOP 收尾
    _run(uc, 0x4ab72f, None, {}, forces, {0x4a33f0: 1}, stop=0x4ab77e)
    return uc.mem_read(rb, 1)[0]


def main():
    ok = True
    print("=== A. 0x4ebcd0(a,b) = sat_sub(a,b) ===")
    for (a, b, w) in [(5, 1, 4), (1, 5, 0), (3, 3, 0), (0, 1, 0), (7, 2, 5),
                      (0x1234, 0x1000, 0x234), (0xFF, 0x10, 0xEF)]:
        got = _ebcd0(a, b)
        ok &= _t("0x4ebcd0(%d,%d) -> %d (want %d)" % (a, b, got, w), got == w)

    print("=== B. 0x49fe40(a,b,N) 矩阵记录低3位=N ===")
    for (N, init, w) in [(0, 0xF0, 0xF0), (2, 0xF0, 0xF2), (4, 0xF0, 0xF4),
                         (6, 0xF0, 0xF6), (7, 0xF3, 0xF7), (3, 0x55, 0x55 & 0xF8 | 3)]:
        got = _fe40(0xC1000, 0xC2000, N, init)
        ok &= _t("0x49fe40(N=%d, init=0x%02x) -> 0x%02x (want 0x%02x)" % (N, init, got, w), got == w)

    print("=== C. 0x4ab680 成功分支：矩阵 low3 = sat_sub(rel,1) ===")
    for rel in (0, 1, 3, 5, 7):
        init = 0xF0
        newrel = sat_sub(rel, 1)
        want = (init & 0xF8) | (newrel & 7)
        got = _ab680_success(rel, init)
        ok &= _t("0x4ab680 成功 rel=%d -> 矩阵 0x%02x (want 0x%02x, newrel=%d)" % (rel, got, want, newrel), got == want)

    print("=== D. 静态结构断言 ===")
    from _dis_helper import disasm
    d0 = " ".join(r["ops"] for r in disasm(0x4ab680, 0x120))
    ok &= _t("0x4ab680 成功分支调 0x49fe40（矩阵写点）", "49fe40" in d0)
    ok &= _t("0x4ab680 经 0x4ebcd0 算 newrel", "4ebcd0" in d0)
    ok &= _t("0x4ab680 经 0x49fd60 取当前 rel", "49fd60" in d0)
    d1 = " ".join(r["ops"] for r in disasm(0x49fe40, 0x30))
    ok &= _t("0x49fe40 调 0x49fd80 取矩阵记录并回写", "49fd80" in d1 and "byte ptr [eax], cl" in d1)

    print()
    print("结果：" + ("全部通过" if ok else "存在失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
