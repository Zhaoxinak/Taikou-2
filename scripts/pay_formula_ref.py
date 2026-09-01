# -*- coding: utf-8 -*-
"""pay_formula_ref.py — 续180(B) 破解 0x49fa40(pay) 公式（Unicorn 实跑验证）

0x49fa40(A) 中 A 指向城表条目（0x51eb88 + cidx*31）。
  esi = (A[0xc] * 300) & 0xffff       # 兵員/規模 × 300，截断 16-bit
  门：0x49f480(A)=国政治条目(国=A[0]); 0x49b550(该条目)=国主实体;
      byte[国主+0x25] == cidx（国主驻此城）才放行，否则走失败分支。
  放行分支：f = 0x49faf0(国主实体)（国石高ベース 知行和，16-bit）
            pay = min( max(esi, 5*f & 0xffff), 50000 )
  失败分支：pay = min( esi, 50000 )

注：静态镜像中国政治链表的知行节点为空，故 0x49faf0 实测恒 0——
     真实放行分支退化为 min(esi,50000) 与失败分支同形。下方用 hook 逼出
     5*f 项以坐实放行分支结构。
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
from itertools import product

from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EBX

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
IMG = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
STACK = 0x7F000
CAS_TBL = 0x51eb88
CAS_STRIDE = 31
KOKU_TBL = 0x5179b8
ENT_TBL = 0x519868
ENT_STRIDE = 47
FUNC = 0x49FA40
RET = 0x90000


def sat_sub(a, b):
    return a - b if a > b else 0


class Emu:
    def __init__(self, hook_f=None):
        self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        self.uc.mem_map(BASE, len(IMG))
        self.uc.mem_write(BASE, IMG)
        self.uc.mem_map(STACK - 0x10000, 0x20000)
        self.uc.mem_map(RET, 0x1000)
        self.uc.mem_write(RET, b"\xc3")
        self.hook_f = hook_f
        if hook_f is not None:
            # 强制放行门（0x49b550 返回 cidx）+ 强制 0x49faf0 返回 hook_f
            self.uc.hook_add(UC_HOOK_CODE, self._h, begin=0x49B550, end=0x49B550)
            self.uc.hook_add(UC_HOOK_CODE, self._h, begin=0x49FAF0, end=0x49FAF0)

    def _h(self, uc, addr, size, ud):
        esp = uc.reg_read(UC_X86_REG_ESP)
        ret = int.from_bytes(uc.mem_read(esp, 4), "little")
        if addr == 0x49B550:
            # 强制放行门：令 al == bl（cidx）。ebx 在调用前 = (A-0x51eb88)/31 = cidx。
            uc.reg_write(UC_X86_REG_EAX, uc.reg_read(UC_X86_REG_EBX) & 0xFF)
        elif addr == 0x49FAF0:
            uc.reg_write(UC_X86_REG_EAX, self.hook_f & 0xFFFF)
        uc.reg_write(UC_X86_REG_ESP, esp + 4)
        uc.reg_write(UC_X86_REG_EIP, ret)

    def run(self, castle_idx, heibei):
        uc = self.uc
        A = CAS_TBL + castle_idx * CAS_STRIDE
        uc.mem_write(A + 0xc, bytes([heibei & 0xFF]))
        esp = STACK
        uc.mem_write(esp, RET.to_bytes(4, "little"))
        uc.mem_write(esp + 4, A.to_bytes(4, "little"))
        uc.reg_write(UC_X86_REG_ESP, esp)
        uc.emu_start(FUNC, RET)
        return uc.reg_read(UC_X86_REG_EAX)


def py_pay(h, f, gate):
    esi = (h * 300) & 0xFFFF
    if gate:
        # 0x49faf0 返回值先 &0xffff，再 ×5（×5 后不截断），与 esi 取大，最后 cap 50000
        f16 = f & 0xFFFF
        eax = max(esi, f16 * 5)
    else:
        eax = esi
    return min(eax, 50000)


def _t(name, cond):
    print(f"  [{'OK' if cond else 'NG'}] {name}")
    return bool(cond)


def main():
    ok = True
    # 1) 真实函数（静态镜像 f=0）→ 放行/失败分支同形 = min(兵员*300&0xffff,50000)
    emu0 = Emu(hook_f=None)
    mism = 0
    for c in (0, 7, 30, 100, 199):
        for h in (0, 1, 10, 50, 100, 167, 200, 255):
            got = emu0.run(c, h)
            want = py_pay(h, 0, True)   # f=0
            if got != want:
                mism += 1
                if mism <= 3:
                    print("    失败样例 c,h:", c, h, "got", got, "want", want)
    ok &= _t("真实函数 兵员×300 主项（40 组一致，f=0 退化）", mism == 0)

    # 2) hook 逼出放行分支 5*f 项：gate=True，f 取多值
    mism = 0
    for (c, h, f) in product((7, 30, 100), (0, 1, 50, 100, 255), (0, 1, 7, 100, 1000, 60000)):
        emu = Emu(hook_f=f)
        got = emu.run(c, h)
        want = py_pay(h, f, True)
        if got != want:
            mism += 1
            if mism <= 5:
                print("    失败样例 c,h,f:", c, h, f, "got", got, "want", want)
    ok &= _t("放行分支 min(max(兵員*300&0xffff, (f&0xffff)*5),50000)（hook f 校验）", mism == 0)

    # 3) 失败分支（hook 门失败：让 0x49b550 返回 0，与 cidx 不等）→ 仅 esi 项
    #    复用 Emu 但门 hook 返回 0
    class EmuFail(Emu):
        def _h(self, uc, addr, size, ud):
            esp = uc.reg_read(UC_X86_REG_ESP)
            ret = int.from_bytes(uc.mem_read(esp, 4), "little")
            if addr == 0x49B550:
                uc.reg_write(UC_X86_REG_EAX, 0)   # 门失败
            elif addr == 0x49FAF0:
                uc.reg_write(UC_X86_REG_EAX, self.hook_f & 0xFFFF)
            uc.reg_write(UC_X86_REG_ESP, esp + 4)
            uc.reg_write(UC_X86_REG_EIP, ret)
    mism = 0
    for (c, h, f) in product((7, 100), (0, 10, 100, 255), (0, 100, 60000)):
        emu = EmuFail(hook_f=f)
        got = emu.run(c, h)
        want = py_pay(h, f, False)
        if got != want:
            mism += 1
            if mism <= 3:
                print("    失败样例 c,h,f:", c, h, f, "got", got, "want", want)
    ok &= _t("失败分支 min((兵員*300)&0xffff,50000)（门失败，f 不参与）", mism == 0)

    # 4) 静态断言：÷31 魔数定位城堡索引、×300 系数、cap 50000、faf0×5
    import sys
    sys.path.insert(0, HERE)
    from _dis_helper import lines
    seg = lines(0x49FA40, 0x9A0).splitlines()
    ok &= _t("÷31 魔数 0x84210843（城堡索引 = (A-0x51eb88)/31）",
             any("0x84210843" in t for t in seg))
    ok &= _t("×300 系数（esi = A[0xc] 经 lea 乘 3*5*5*4）",
             any("eax + eax*2" in t for t in seg))
    ok &= _t("cap 50000 (0xc350) 两处（放行+失败）",
             sum(t.count("0xc350") for t in seg) >= 2)
    ok &= _t("5*f：放行分支 lea eax,[eax+eax*4]（×5）",
             any("eax + eax*4" in t for t in seg))

    print()
    print("结果：" + ("全部通过" if ok else "存在失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
