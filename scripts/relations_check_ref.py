# -*- coding: utf-8 -*-
"""relations_check_ref.py — 进贡/外交行动 成功判定 `0x4ab870` 公式 + Unicorn 实跑验证（续179）

清单 P2「进贡/威吓/朝廷/谋略 关系变动量」的静态解码 + emu 验证。

## 解码（0x4ab680 门链 → 0x4ab870 概率判定）
`0x4ab680(ctx)`（同族 0x4ab8f0/0x4ab3c0/0x4aa690 头部同构）：
  - edi = 国政治表[ctx[0x24]]（ctx 所在国）
  - esi = 国政治表[word[ctx+0x18] & 0xff]（对象国）
  - word[esi+4] >= 0x172（对象国无当主）→ ret 2
  - 0x4ab7a0 / 0x4ab830 / 0x4ab850 三道资格门（任一非 0 → ret 0）
  - call 0x4ab870(ctx, edi, esi) → 布尔成功判定

`0x4ab870(arg1=ctx, arg2=国1政, arg3=国2政)`：
  dl  = ctx[0x2d] & 7
  cl  = ctx[0xf]  & 3
  si  = ctx[0xd]                 (byte)
  edi = si + 5 * (sat_sub(dl, 3) + 2*cl)          ← 阈值 threshold
  rel = 0x49fd60(arg1', arg3') & 7                (关系值 0..7, 经 0x49fd80)
  ent = 0x49f5a0(arg3')  → lord entity            (word[x+4] → 实体 0x519868+i*47)
  v   = byte[ent + 0xd]                           (当主五维之一)
  r   = 0x4ebd60(v + 10*rel)                      ← rand() % (v + 10*rel)
  return (r + 15*rel >= threshold) ? 1 : 0

## Unicorn 验证策略
hook 三个外部依赖（0x4ebd60=rand、0x49fd60=rel、0x49f5a0=entity）返回受控值，
对多组 (ctx 字节, rel, v) 穷举比较 emu 实跑结果与 Python 公式。
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

from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX,
                                UC_X86_REG_ESP)

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
IMG = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()

STACK = 0x7F000
SCRATCH = 0x90000          # 放 ctx 假结构
FUNC = 0x4AB870
HOOKS = {0x4EBD60: "rand", 0x49FD60: "rel", 0x49F5A0: "ent"}


def sat_sub(a, b):
    return a - b if a > b else 0


def py_formula(ctx_bytes, rel, v):
    dl = ctx_bytes[0x2D] & 7
    cl = ctx_bytes[0xF] & 3
    si = ctx_bytes[0xD]
    threshold = si + 5 * (sat_sub(dl, 3) + 2 * cl)
    r = v + 10 * rel          # rand()%(v+10*rel) 取上界（最易成功）与 0（最难）都测
    return {
        "threshold": threshold,
        "pass_max": int((r + 15 * rel) >= threshold),
        "pass_min": int((0 + 15 * rel) >= threshold),
    }


class Emu:
    def __init__(self):
        self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        self.uc.mem_map(BASE, len(IMG))
        self.uc.mem_write(BASE, IMG)
        self.uc.mem_map(STACK - 0x10000, 0x20000)
        self.uc.mem_map(SCRATCH, 0x1000)
        self.rand_val = 0
        self.rel_val = 0
        self.ent_val = 0
        self.uc.hook_add(UC_HOOK_CODE, self._hook, begin=0x4EBD60, end=0x4EBD60)
        self.uc.hook_add(UC_HOOK_CODE, self._hook, begin=0x49FD60, end=0x49FD60)
        self.uc.hook_add(UC_HOOK_CODE, self._hook, begin=0x49F5A0, end=0x49F5A0)

    def _hook(self, uc, addr, size, ud):
        # 伪造返回值并 ret（栈上已有返回地址）
        esp = uc.reg_read(UC_X86_REG_ESP)
        ret = int.from_bytes(uc.mem_read(esp, 4), "little")
        if addr == 0x4EBD60:
            uc.reg_write(UC_X86_REG_EAX, self.rand_val)
        elif addr == 0x49FD60:
            uc.reg_write(UC_X86_REG_EAX, self.rel_val)
        elif addr == 0x49F5A0:
            # 返回 scratch 实体指针，其 +0xd = ent_val
            uc.reg_write(UC_X86_REG_EAX, SCRATCH + 0x100)
        uc.reg_write(UC_X86_REG_ESP, esp + 4)
        uc.reg_write(UC_X86_REG_ECX, ret)  # 便于调试
        # 直接跳回返回地址
        from unicorn.x86_const import UC_X86_REG_EIP
        uc.reg_write(UC_X86_REG_EIP, ret)

    def run(self, ctx_bytes, rel, v, rand_val):
        self.rel_val = rel
        self.rand_val = rand_val
        uc = self.uc
        uc.mem_write(SCRATCH, b"\x00" * 0x1000)
        uc.mem_write(SCRATCH + 0x100 + 0xD, bytes([v]))
        uc.mem_write(SCRATCH + 0x200, ctx_bytes)
        # 栈布局：[ret][arg1=ctx][arg2][arg3]
        esp = STACK
        uc.mem_write(esp + 4, (SCRATCH + 0x200).to_bytes(4, "little"))  # arg1 ctx
        uc.mem_write(esp + 8, (0x5179B8 + 14).to_bytes(4, "little"))    # arg2
        uc.mem_write(esp + 12, (0x5179B8 + 28).to_bytes(4, "little"))   # arg3
        uc.reg_write(UC_X86_REG_ESP, esp)
        uc.emu_start(FUNC, 0)
        return uc.reg_read(UC_X86_REG_EAX) & 0xFFFF


def _t(name, cond):
    print(f"  [{'OK' if cond else 'NG'}] {name}")
    return bool(cond)


def main():
    emu = Emu()
    ok = True
    cases = 0
    mismatches = []
    # 穷举代表性输入
    import itertools
    for a, b, c, rel, v, rv in itertools.product(
            [0, 3, 7, 9], [0, 1, 2, 3, 5], [0, 50, 200],
            [0, 1, 4, 7], [10, 60, 100], [0, 37, 999]):
        ctx = bytearray(0x30)
        ctx[0x2D] = a
        ctx[0xF] = b
        ctx[0xD] = c
        got = emu.run(bytes(ctx), rel, v, rv)
        # Python 公式重算（rand_val=rv）
        dl = a & 7
        cl = b & 3
        threshold = c + 5 * (sat_sub(dl, 3) + 2 * cl)
        want = 1 if (rv + 15 * rel) >= threshold else 0
        cases += 1
        if got != want:
            mismatches.append((a, b, c, rel, v, rv, got, want))
    ok &= _t(f"公式穷举 {cases} 组全部一致", not mismatches)
    for m in mismatches[:5]:
        print("    失败样例:", m)

    print("-- 公式静态断言（pickle 反汇编） --")
    import pickle
    d, starts = pickle.load(open(os.path.join(HERE, "_insn_addrs.pkl"), "rb"))
    txt = {off: s[1] for off, s in d.items()}
    seg = [txt.get(o - BASE, "") for o in range(0x4AB870, 0x4AB8E8)]
    ok &= _t("0x4ab878 读 ctx[0x2d]", any("byte ptr [eax + 0x2d]" in t for t in seg))
    ok &= _t("0x4ab87b 读 ctx[0xf]", any("byte ptr [eax + 0xf]" in t for t in seg))
    ok &= _t("0x4ab87e 读 ctx[0xd]", any("byte ptr [eax + 0xd]" in t for t in seg))
    ok &= _t("sat_sub(dl,3)：push 3 + call 0x4ebcd0",
             any(t.startswith("push 3") for t in seg) and
             any("call 0x4ebcd0" in t for t in seg))
    ok &= _t("rand：call 0x4ebd60 存在", any("call 0x4ebd60" in t for t in seg))
    ok &= _t("rel_lookup：call 0x49fd60 存在", any("call 0x49fd60" in t for t in seg))
    ok &= _t("当主实体：call 0x49f5a0 存在", any("call 0x49f5a0" in t for t in seg))
    ok &= _t("×5 系数：lea [eax+eax*4] 族",
             any("lea" in t and "eax*4" in t for t in seg))
    ok &= _t("×15 系数：lea [ecx+ecx*4] 叠 ×3",
             any("[ecx + ecx*4]" in t for t in seg) and
             any("[esi + esi*2]" in t for t in seg))
    ok &= _t("布尔收尾：cmp ax,di + sbb/inc",
             any(t.startswith("cmp ax, di") for t in seg) and
             any(t.startswith("sbb eax, eax") for t in seg))

    print()
    print("结果：" + ("全部通过" if ok else "存在失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
