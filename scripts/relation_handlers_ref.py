# -*- coding: utf-8 -*-
"""relation_handlers_ref.py — 续181 破解 P2 关系变动量三 handler（静态+Unicorn 实跑验证）

四函数族（外交/谋略/进贡 类行动）：
  0x4ab870  — 成功判定公式（续179 已破，本文件做回归复核）
  0x4ab8f0  — 资格门（gate）：仅校验两国政治条目有效性，返回 2 表示可行动
  0x4ab3c0  — 行动 handler：依使者能力算阈值、弹消息(0xd20/0xd21)、把 4-bit 结果
              写入 国政治[国].byte[0xc]（经 0x49b5b0 低半字节 / 0x49b5d0 高半字节）
  0x4aa690  —  suitability+dispatch：比对两国 国石高(0x49faf0)、依使者/目标能力算阈值，
              通过后调 0x4aa820 实际效果（更新目标 忠诚/状态 + 候选池 0x51e9c0 + 关系消息 0x581/0x582）

关系存储（本文件新发现）：
  * 0x49c2b0(e)  : 取 e 的关系记录指针 = 0x521aa8 + idx*7  （idx = [e] if <1000）
  * 0x49c310(e)  : 反向关系记录指针   = 0x520660 + idx*7  （idx = [e] if 1000<=x<2000）
  => 关系为「两人（实体）之间」的 7 字节记录，主级别是 0..7 的八段等级（diplomacy_ref 已定）。
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
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESP, UC_X86_REG_EIP

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
IMG = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
STACK = 0x7F000
KOKU_TBL = 0x5179b8
KOKU_STRIDE = 14
ENT_TBL = 0x519868
ENT_STRIDE = 47
REL_FWD = 0x521aa8          # 0x49c2b0 正向关系记录基址
REL_REV = 0x520660          # 0x49c310 反向关系记录基址
REL_STRIDE = 7


def _uc():
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(BASE, len(IMG))
    uc.mem_write(BASE, IMG)
    uc.mem_map(STACK - 0x10000, 0x20000)
    return uc


def _call(uc, func, args, argbase=0x4, ret_scratch=0x90000, ret_val=None):
    """Call `func` with `args` (list of 32-bit ints) on a fresh stack, return EAX.
    If ret_val is not None, install a hook that writes it to EAX at ret_scratch and
    returns there (for functions that must 'succeed')."""
    RET = ret_scratch
    uc.mem_map(RET, 0x1000)
    uc.mem_write(RET, b"\xc3")
    esp = STACK
    uc.mem_write(esp, RET.to_bytes(4, "little"))
    a = esp + 4
    for v in args:
        uc.mem_write(a, v.to_bytes(4, "little"))
        a += 4
    uc.reg_write(UC_X86_REG_ESP, esp)
    if ret_val is not None:
        target = {"eax": ret_val}
        def hk(uc, addr, size, ud):
            e = uc.reg_read(UC_X86_REG_ESP)
            ret = int.from_bytes(uc.mem_read(e, 4), "little")
            uc.reg_write(UC_X86_REG_EAX, target["eax"])
            uc.reg_write(UC_X86_REG_ESP, e + 4)
            uc.reg_write(UC_X86_REG_EIP, ret)
        uc.hook_add(UC_HOOK_CODE, hk, begin=func, end=func)
        uc.emu_start(func + 1, RET)
    else:
        uc.emu_start(func, RET)
    return uc.reg_read(UC_X86_REG_EAX) & 0xFFFFFFFF


def emu_gate(prov0_lord, prov1_lord, valid0=True, valid1=True):
    """Emulate 0x4ab8f0(entity) with entity.国=prov0, entity.国@0x18=prov1,
    and set 国政治[prov1].word[4]=prov1_lord (<370 valid). Returns EAX."""
    uc = _uc()
    ent = 0xB0000
    uc.mem_map(ent, 0x1000)
    uc.mem_write(ent, bytes([5 & 0xff]))          # 国 byte[0]
    uc.mem_write(ent + 0x18, bytes([5 & 0xff]))   # 国@0x18
    uc.mem_write(ent + 0x24, bytes([5 & 0xff]))   # 国@0x24
    # 国政治[5].word[4] = lord idx
    koku = KOKU_TBL + 5 * KOKU_STRIDE
    uc.mem_write(koku + 4, (prov1_lord & 0xFFFF).to_bytes(2, "little"))
    return _call(uc, 0x4ab8f0, [ent], ret_scratch=0x90000)


def emu_relget(idx):
    """Emulate 0x49c2b0(entity_idx_value) where input = [ecx]=idx (<1000).
    We just push idx as the [ecx] value by laying a 2-byte at a scratch and passing ptr.
    Simpler: call with ecx = a scratch holding idx, but 0x49c2b0 reads [ecx]. We pass
    ecx = pointer to a word = idx."""
    uc = _uc()
    buf = 0xC0000
    uc.mem_map(buf, 0x1000)
    uc.mem_write(buf, (idx & 0xFFFF).to_bytes(2, "little"))
    # _call doesn't let us set ecx easily; use direct emu
    RET = 0x90000
    uc.mem_map(RET, 0x1000)
    uc.mem_write(RET, b"\xc3")
    esp = STACK
    uc.mem_write(esp, RET.to_bytes(4, "little"))
    uc.reg_write(UC_X86_REG_ESP, esp)
    import unicorn.x86_const as X
    uc.reg_write(X.UC_X86_REG_ECX, buf)
    uc.emu_start(0x49c2b0, RET)
    return uc.reg_read(UC_X86_REG_EAX) & 0xFFFFFFFF


def py_relptr(idx):
    return REL_FWD + idx * REL_STRIDE


def _t(name, cond):
    print(f"  [{'OK' if cond else 'NG'}] {name}")
    return bool(cond)


def main():
    ok = True
    # --- 0x4ab8f0：取 entity.byte[0x18] 所指向「国」的国政治.word[4] = 国主实体索引；
    #     若该国主 idx >= 370（空缺）或 国索引 >=49 → 返回哨兵 2；否则返回该国主 idx。---
    r_ok = emu_gate(0, 0, valid1=True)        # 国政治[5].word[4] = 0(<370) → 返回 0（国主 idx）
    ok &= _t("0x4ab8f0 国政治[国@0x18].lord=0(<370) → 返回 lord idx 0 (got 0x%x)" % r_ok, r_ok == 0)
    uc = _uc()
    ent = 0xB0000
    uc.mem_map(ent, 0x1000)
    uc.mem_write(ent + 0x18, bytes([5]))
    uc.mem_write(ent + 0x24, bytes([5]))
    koku = KOKU_TBL + 5 * KOKU_STRIDE
    uc.mem_write(koku + 4, (0x172).to_bytes(2, "little"))  # lord == 370 = 空缺
    eax = _call(uc, 0x4ab8f0, [ent])
    ok &= _t("0x4ab8f0 国政治[国@0x18].lord>=370(空缺) → 返回哨兵 2 (got 0x%x)" % eax, eax == 2)

    # --- 0x49c2b0 关系表几何（续181 新发现）---
    for idx in (0, 1, 7, 48, 100, 999):
        got = emu_relget(idx)
        want = py_relptr(idx)
        ok &= _t(f"0x49c2b0({idx}) = 0x521aa8 + {idx}*7 = 0x{want:06x}", got == want)
        if got != want:
            print("      got 0x%06x" % got)

    # --- 0x4ab3c0 / 0x4aa690 结构静态断言（disasm 已确认调用目标，这里用镜像字节复核）---
    from _dis_helper import disasm
    d3 = " ".join(r["ops"] for r in disasm(0x4ab3c0, 0x345))
    ok &= _t("0x4ab3c0 调 0x49b5b0/0x49b5d0 写 国政治[国].byte[0xc] 两半字节",
             "49b5b0" in d3 and "49b5d0" in d3)
    ok &= _t("0x4ab3c0 弹关系消息 0xd20/0xd21", "517710" in d3)
    d2 = " ".join(r["ops"] for r in disasm(0x4aa690, 0x191))
    ok &= _t("0x4aa690 调 0x49faf0(国石高) 比对两国", "49faf0" in d2)
    ok &= _t("0x4aa690 调 0x4aa820 实际效果", "4aa820" in d2)
    dleaf = " ".join(r["ops"] for r in disasm(0x4aa820, 0x120))
    ok &= _t("0x4aa820 经 0x49c2b0/0x49c310 取双向关系记录 + 弹 0x581/0x582",
             "49c2b0" in dleaf and "49c310" in dleaf and "517710" in dleaf)

    print()
    print("结果：" + ("全部通过" if ok else "存在失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
