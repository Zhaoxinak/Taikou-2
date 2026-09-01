# -*- coding: utf-8 -*-
"""naisei_resource_ref.py — 軍糧/米/資金 城纳结算 `0x4a5fc0` + Unicorn 实跑验证（续179）

清单 P1「内政 軍糧/米/資金 handler 精确 delta（含随机项）」——**「随机项」前提证伪**：
本函数族全链（0x4a5fc0/0x4a61d0 及其全部被调 helper）无一处 call 0x4ebd60(rand)，
delta 全部为确定性的 sat_add/sat_sub 流转。

## 解码 `0x4a5fc0(A)`（A = 部队/工作记录 struct）
门：A[0x1b]&0x10 置位或 城tbl[0x1b]&0x10 置位 → 直接返回；
    0x49ac90(A) 或 0x4a5c40(A) 非 0 才继续。
实体链：ent = 0x519868 + word[A+0xa]*47；castle = 0x51eb88 + byte[ent+0x25]*31。

三笔转移（A → 城，均为「A 扣减、城 sat_add」）：
  1. 軍糧(+0x14, cap 30000)：
     d1 = min( sat_sub(A.r14, A.r10//5),  sat_sub(30000, castle.r14) )
     A.r14 = sat_sub(A.r14, d1)；castle.r14 = min(castle.r14+d1, 30000)
  2. 米(+0x12, cap 30000)：
     d2 = min( sat_sub(A.r12, 500),  sat_sub(30000, castle.r12) )
     A.r12 = sat_sub(A.r12, d2)；castle.r12 = min(castle.r12+d2, 30000)
  3. 資金(+0x10, cap 50000)：
     pay = 0x49fa40(A)（兵员/规模函数，深链）
     g   = 0x4a6140(castle)（国主==城主时 = word[0x525918 + 国*2]，运行期表；否则 0）
     d3 = min( sat_sub(A.r10, pay),  sat_sub(g, castle.r10) )
     d3 = (d3 // 10) * 10                       ← 落到 10 的倍数（÷10 魔数 sar2 + ×10）
     A.r10 = sat_sub(A.r10, d3)；castle.r10 = min(castle.r10+d3, 50000)

包装器族（供 Godot 复刻直接用）：
  0x4a33a0: castle.r10 = sat_add(.r10, d, 50000)   0x4a33d0: .r10 = sat_sub(.r10, d)
  0x4a33f0: .r12      = sat_add(.r12, d, 30000)   0x4a3420: .r12 = sat_sub(.r12, d)
  0x4a3440: .r14      = sat_add(.r14, d, 30000)   0x4a3470: .r14 = sat_sub(.r14, d)
反向 `0x4a61d0`（城→A 支给）已定位，头部门链同构（用 0x49f480+0x49b550 找城）。

## Unicorn 验证
hook 0x49ac90(→1)/0x49fa40(→pay)/0x4a6140(→g)，实体/城表写受控值，
穷举多组 (A 资源, 城资源, pay, g) 比较 emu 与 Python 公式（含 0 除/越界/上限钳制）。
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
import itertools

from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESP

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
IMG = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()

STACK = 0x7F000
SCRATCH = 0x90000
FUNC = 0x4A5FC0
ENT_TBL = 0x519868
CAS_TBL = 0x51eb88
ENT_STRIDE = 47
CAS_STRIDE = 31


def sat_add(a, b, cap):
    return min(a + b, cap)


def sat_sub(a, b):
    return a - b if a > b else 0


def py_settle(r10, r12, r14, cr10, cr12, cr14, pay, g):
    # 1) 軍糧
    d1 = min(sat_sub(r14, r10 // 5), sat_sub(30000, cr14))
    r14 = sat_sub(r14, d1)
    cr14 = sat_add(cr14, d1, 30000)
    # 2) 米
    d2 = min(sat_sub(r12, 500), sat_sub(30000, cr12))
    r12 = sat_sub(r12, d2)
    cr12 = sat_add(cr12, d2, 30000)
    # 3) 資金
    d3 = min(sat_sub(r10, pay), sat_sub(g, cr10))
    d3 = (d3 // 10) * 10
    r10 = sat_sub(r10, d3)
    cr10 = sat_add(cr10, d3, 50000)
    return dict(a_r10=r10, a_r12=r12, a_r14=r14,
                c_r10=cr10, c_r12=cr12, c_r14=cr14, d1=d1, d2=d2, d3=d3)


class Emu:
    def __init__(self):
        self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        self.uc.mem_map(BASE, len(IMG))
        self.uc.mem_write(BASE, IMG)
        self.uc.mem_map(STACK - 0x10000, 0x20000)
        self.uc.mem_map(SCRATCH, 0x1000)
        self.pay = 0
        self.g = 0
        self.uc.hook_add(UC_HOOK_CODE, self._hook, begin=0x49AC90, end=0x49AC90)
        self.uc.hook_add(UC_HOOK_CODE, self._hook, begin=0x49FA40, end=0x49FA40)
        self.uc.hook_add(UC_HOOK_CODE, self._hook, begin=0x4A6140, end=0x4A6140)

    def _hook(self, uc, addr, size, ud):
        esp = uc.reg_read(UC_X86_REG_ESP)
        ret = int.from_bytes(uc.mem_read(esp, 4), "little")
        if addr == 0x49AC90:
            uc.reg_write(UC_X86_REG_EAX, 1)          # 资格门放行
        elif addr == 0x49FA40:
            uc.reg_write(UC_X86_REG_EAX, self.pay)
        elif addr == 0x4A6140:
            uc.reg_write(UC_X86_REG_EAX, self.g)
        uc.reg_write(UC_X86_REG_ESP, esp + 4)
        from unicorn.x86_const import UC_X86_REG_EIP
        uc.reg_write(UC_X86_REG_EIP, ret)

    def run(self, A, castle, pay, g):
        uc = self.uc
        self.pay, self.g = pay, g
        # A @ scratch：+0xa=实体idx(word)、+0x10/12/14 资源、+0x1b=0
        uc.mem_write(SCRATCH, b"\x00" * 0x40)
        uc.mem_write(SCRATCH + 0xA, (3).to_bytes(2, "little"))      # 实体 idx 3
        for off, val in ((0x10, A[0]), (0x12, A[1]), (0x14, A[2])):
            uc.mem_write(SCRATCH + off, (val & 0xFFFF).to_bytes(2, "little"))
        # 实体[3].+0x25 = 7（城 idx）
        ent = ENT_TBL + 3 * ENT_STRIDE
        uc.mem_write(ent + 0x25, bytes([7]))
        # 城 7：+0x10/12/14 资源、+0x1b=0
        cas = CAS_TBL + 7 * CAS_STRIDE
        uc.mem_write(cas + 0x1A, b"\x00\x00")   # +0x1b 清零（含对齐）
        for off, val in ((0x10, castle[0]), (0x12, castle[1]), (0x14, castle[2])):
            uc.mem_write(cas + off, (val & 0xFFFF).to_bytes(2, "little"))
        esp = STACK
        uc.mem_write(esp + 4, SCRATCH.to_bytes(4, "little"))
        uc.reg_write(UC_X86_REG_ESP, esp)
        uc.emu_start(FUNC, 0)
        a = [int.from_bytes(uc.mem_read(SCRATCH + o, 2), "little")
             for o in (0x10, 0x12, 0x14)]
        c = [int.from_bytes(uc.mem_read(cas + o, 2), "little")
             for o in (0x10, 0x12, 0x14)]
        return a, c


def _t(name, cond):
    print(f"  [{'OK' if cond else 'NG'}] {name}")
    return bool(cond)


def main():
    emu = Emu()
    cases = mismatches = 0
    ok = True
    # A=(資金,米,軍糧), castle 同序, pay, g
    for (a10, a12, a14, c10, c12, c14, pay, g) in itertools.product(
            [0, 5, 499, 500, 1234, 50000], [0, 100, 499, 501, 30000],
            [0, 100, 999, 30000], [0, 123, 49999, 50000],
            [0, 100, 29999, 30000], [0, 100, 29999, 30000],
            [0, 100, 999], [0, 100, 999, 60000]):
        # 过滤掉一部分指数爆炸（采样）
        if (a10 + a12 + c14 + pay + g) % 7 != 0 and (a10 * 31 + c12) % 5 != 0:
            continue
        got_a, got_c = emu.run((a10, a12, a14), (c10, c12, c14), pay, g)
        want = py_settle(a10, a12, a14, c10, c12, c14, pay, g)
        cases += 1
        if (got_a[0], got_a[1], got_a[2]) != (want["a_r10"], want["a_r12"], want["a_r14"]) or \
           (got_c[0], got_c[1], got_c[2]) != (want["c_r10"], want["c_r12"], want["c_r14"]):
            mismatches += 1
            if mismatches <= 3:
                print("    失败样例:", (a10, a12, a14, c10, c12, c14, pay, g),
                      "got", got_a, got_c, "want", want)
    ok &= _t(f"结算公式穷举 {cases} 组一致（失败 {mismatches}）", mismatches == 0)

    print("-- 静态断言（pickle 反汇编） --")
    import pickle
    d, starts = pickle.load(open(os.path.join(HERE, "_insn_addrs.pkl"), "rb"))
    txt = {off: s[1] for off, s in d.items()}
    seg = [txt.get(o - BASE, "") for o in range(0x4A5FC0, 0x4A612D)]
    # cap 立即数分布在两处：主函数 2×push 0x7530（sat_sub(30000, castle.x) 余量）
    # + 包装器族 0x4a33a0..0x4a348d（0x4a33a7 push 0xc350 資金、0x4a33f7/0x4a3447 push 0x7530 米/軍糧）
    wrap = [txt.get(o - BASE, "") for o in range(0x4A33A0, 0x4A348D)]
    ok &= _t("÷5 魔数（軍糧义务 = 資金/5）",
             any("0x66666667" in t for t in seg))
    ok &= _t("÷10 魔数 + ×10（資金取整到 10 倍数）",
             any("sar edx, 2" in t for t in seg) and
             any("[edx + edx*4]" in t for t in seg))
    ok &= _t("cap 50000 (0xc350)@包装器0x4a33a7 資金(+0x10)",
             any("0xc350" in t for t in wrap))
    ok &= _t("cap 30000 (0x7530) 合并 4 处（主函数2+包装器2）",
             sum(t.count("0x7530") for t in seg) == 2 and
             sum(t.count("0x7530") for t in wrap) == 2)
    ok &= _t("包装器族 6 个 call 目标齐全",
             all(any(f"call 0x{f:06x}" in t for t in seg)
                 for f in (0x4A33A0, 0x4A33D0, 0x4A33F0, 0x4A3420, 0x4A3440, 0x4A3470)))
    ok &= _t("无 rand：0x4a5fc0..0x4a612d 无 call 0x4ebd60",
             not any("call 0x4ebd60" in t for t in seg))

    print()
    print("结果：" + ("全部通过" if ok else "存在失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
