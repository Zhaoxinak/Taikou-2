# -*- coding: utf-8 -*-
"""battle_sectionA_ref.py — 续182 破解合战 §10 残留：section A 9 类实体访问器（Unicorn 实跑验证）

section A = 0x512e58 处 180B = 9 个兵种/部队类别(a=0..8) × 20 个属性(c=0..19)，stride 20，每格 1 字节。
  * 0x439050 getLo(a,c) = section_A[a*20 + c] & 0xf      （低 4 位 = 攻击除数表索引/单位类型码，被 0x43a9c0 吃）
  * 0x4390c0 getHi(a,c) = (section_A[a*20 + c] >> 4) & 0xf （高 4 位 = 双方除数 ±1 修饰，实战多恒 0）

调用约定（BATTLE_SPEC §2）：arg1=ecx=c(属性), arg2=eax=a(兵种类别)，均 &0xff。
静态镜像 section A 数据由 C:HJMAPDAT.DAT 在战斗初始化时载入 0x512e58（本验证直接读脱壳镜像字节）。

结论：所谓「9 类实体」= 9 行兵种类别索引 a∈[0,8]；访问器按 stride 20 取 (a,c) 字节的低/高半字节。
兵种「中文名」映射不在 EXE 静态段（BATTLE_SPEC §8 已证伪 MSGX/名表路径），属独立未定位项，不在此条范围。
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
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESP

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
IMG = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
STACK = 0x7F000
SECT_A = 0x512e58


def emu_call(func, a, c):
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(BASE, len(IMG))
    uc.mem_write(BASE, IMG)
    uc.mem_map(STACK - 0x10000, 0x20000)
    RET = 0x90000
    uc.mem_map(RET, 0x1000)
    uc.mem_write(RET, b"\xc3")
    esp = STACK
    uc.mem_write(esp, RET.to_bytes(4, "little"))
    uc.mem_write(esp + 4, (c & 0xff).to_bytes(4, "little"))
    uc.mem_write(esp + 8, (a & 0xff).to_bytes(4, "little"))
    uc.reg_write(UC_X86_REG_ESP, esp)
    uc.emu_start(func, RET)
    return uc.reg_read(UC_X86_REG_EAX) & 0xff


def py_getlo(a, c):
    off = SECT_A - BASE + a * 20 + c
    return IMG[off] & 0xf


def py_gethi(a, c):
    off = SECT_A - BASE + a * 20 + c
    return (IMG[off] >> 4) & 0xf


def _t(name, cond):
    print(f"  [{'OK' if cond else 'NG'}] {name}")
    return bool(cond)


def main():
    ok = True
    lo_fail = hi_fail = 0
    for a in range(9):
        for c in range(20):
            got_lo = emu_call(0x439050, a, c)
            want_lo = py_getlo(a, c)
            if got_lo != want_lo:
                lo_fail += 1
                if lo_fail <= 5:
                    print("    getLo NG a=%d c=%d got=%d want=%d" % (a, c, got_lo, want_lo))
            got_hi = emu_call(0x4390c0, a, c)
            want_hi = py_gethi(a, c)
            if got_hi != want_hi:
                hi_fail += 1
                if hi_fail <= 5:
                    print("    getHi NG a=%d c=%d got=%d want=%d" % (a, c, got_hi, want_hi))
    ok &= _t("getLo(a,c)=section_A[a*20+c]&0xf 全 9×20=180 格一致（失 %d）" % lo_fail, lo_fail == 0)
    ok &= _t("getHi(a,c)=(section_A[a*20+c]>>4)&0xf 全 9×20=180 格一致（失 %d）" % hi_fail, hi_fail == 0)

    # 静态断言：访问器确实索引 0x512e58（stride 20）
    from _dis_helper import disasm
    d = " ".join(r["ops"] for r in disasm(0x439050, 0x24))
    ok &= _t("0x439050 基址 0x512e58 + a*20 + c（lea [ecx+eax*4+0x512e58]）", "512e58" in d)
    d2 = " ".join(r["ops"] for r in disasm(0x4390c0, 0x24))
    ok &= _t("0x4390c0 同基址 + shr 4（高半字节）", "512e58" in d2 and "4" in d2)

    print()
    print("结果：" + ("全部通过" if ok else "存在失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
