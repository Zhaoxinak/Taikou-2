# -*- coding: utf-8 -*-
"""relation_delta_writes_ref.py — 续184 破解 关系 ±delta 实际写点（续181 仍未知项）

关键结论（emu + 反汇编双确认）：

1. 关系三 handler 中，**唯一真正的"写入 delta"是 国政治[prov].byte[0xc]**：
   0x4ab3c0（进贡/威吓/朝廷/谋略 行动 handler）成功后：
     - 读取旧 level = 国政治[prov].byte[0xc] & 0xf
     - 新 level = level + 1
     - 低 4 位 经 0x49b5b0(val, prov) 写入  = 新 level（0..9，10=封顶）
     - 高 4 位 经 0x49b5d0(val, prov) 写入  = quality：
         * 若 新level<5  → quality = 0x4ab300(新level, prov) = 同 level 下其它国未占用的"最小"高半字节（碰撞避免，确定性取最小）
         * 若 新level>=5 → quality = 0
         * 若 新level==10（封顶）→ quality 由 国主实体.word[0x2] 强制：13→2 / 16→1 / 695→1 / 其它→0
   即 byte[0xc] = (quality<<4) | level ，是"国与参照势力外交等级/亲善度"寄存器，成功行动 +1。

2. **0x49b5b0 / 0x49b5d0 是纯位写入助手**（disasm 实锤）：
     0x49b5b0(v,prov): byte[0xc] = (byte[0xc]&0xf0) | (v & 0xff)   # 写低半字节（调用方 v<=0xf）
     0x49b5d0(v,prov): byte[0xc] = (byte[0xc]&0xf)  | (v<<4)       # 写高半字节（调用方 v<=0xf）

3. **0x4aa820 不写任何 delta**（推翻"更新忠诚/状态"旧假设）：它只当 actor 在主人公国且为合法目标时，
   用关系指针调 0x47b900 把消息 0x581/0x582 格式化进 0x517710，再 0x47c080 显示。
   忠诚/状态 delta 由 0x4ab870 成功路径（续179 已破）在调用本簇之前处理，不在本簇。

4. 0x4aa690 是 suitability+dispatch：校验 actor/recipient 诸多资格门（同城、recipient 为家臣、
   loyalty<100、0x49a610 资格、0x4a00a0/0x4a04a0 检查），并按 国石高(0x49faf0) 与 actor 能力
   算出阈值，rand 过阈值才 call 0x4aa820 显示消息；不写 delta。

注：0x4ab300 的参数位于非标准偏移：level 在 [esp+0x34](=entry_esp+0x8)，prov 在 [esp+0x40](=entry_esp+0x14)。
本脚本用偏移式入参精确对齐。
"""
import os
import sys
import struct
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESP, UC_X86_REG_ECX, UC_X86_REG_EIP

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
IMG = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
STACK = 0x7F000
RET = 0x90000
KOKU = 0x5179b8
KOKU_STRIDE = 14
ENT = 0x519868
ENT_STRIDE = 47


def R8(va):
    return IMG[va - BASE]


def R16(va):
    return struct.unpack_from("<H", IMG, va - BASE)[0]


# ---- emu harness（偏移式入参，精确对齐非标准调用约定）----
def _uc():
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(BASE, len(IMG))
    uc.mem_write(BASE, IMG)
    uc.mem_map(STACK - 0x10000, 0x20000)
    uc.mem_map(RET, 0x1000)
    uc.mem_write(RET, b"\xc3")
    return uc


FORCE = {}       # {addr: eax}  — 强制返回值
FORCE_ARGC = {}   # {addr: nargs} — stdcall 约定：callee 清栈 nargs*4（仅推进 ESP）
STOP = RET


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


def _run(uc, func, ecx, argmap, forces, force_argc=None):
    global FORCE, FORCE_ARGC
    FORCE = dict(forces)
    FORCE_ARGC = dict(force_argc or {})
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
    uc.emu_start(func, RET)
    return uc.reg_read(UC_X86_REG_EAX) & 0xFFFFFFFF


def _t(name, cond):
    print("  [%s] %s" % ("OK" if cond else "NG", name))
    return bool(cond)


# ---- python 模型 ----
def py_ab300_free(level, prov):
    """复刻 0x4ab300 的自由高半字节集合（读真实 IMG 国政治表）。level>4 → {0}。"""
    if level > 4:
        return {0}
    occ = set()
    for i in range(49):
        if i == prov:
            continue
        lord = R16(KOKU + i * KOKU_STRIDE + 4)
        if lord >= 0x172:
            continue
        b = R8(KOKU + i * KOKU_STRIDE + 0xC)
        if (b & 0xF) == level:
            occ.add((b >> 4) & 0xF)
    return set(range(16)) - occ


def _ab300(level, prov):
    """emu 调用 0x4ab300(level@8, prov@0x14)，0x4ebd60 强制 0 → 返回确定性最小自由高半字节。"""
    uc = _uc()
    return _run(uc, 0x4ab300, None, {8: level, 0x14: KOKU + prov * KOKU_STRIDE}, {0x4ebd60: 0})


def main():
    ok = True

    # === A. 0x49b5b0 低半字节写入助手（调用方传入 v<=0xf）===
    for base in (0x00, 0x3C, 0xA5, 0xF0):
        for val in (0, 1, 3, 9, 0xF):
            uc = _uc()
            buf = 0xC0000
            uc.mem_map(buf, 0x1000)
            uc.mem_write(buf + 0xC, bytes([base]))
            _run(uc, 0x49b5b0, buf, {4: val}, {})
            got = uc.mem_read(buf + 0xC, 1)[0]
            want = (base & 0xF0) | (val & 0x0F)
            ok &= _t("0x49b5b0 低半字节: 0x%02x|v=%d -> 0x%02x (want 0x%02x)" % (base, val, got, want), got == want)

    # === B. 0x49b5d0 高半字节写入助手（调用方传入 v<=0xf）===
    for base in (0x00, 0xC3, 0x5A, 0x0F):
        for val in (0, 2, 7, 0xF):
            uc = _uc()
            buf = 0xC0000
            uc.mem_map(buf, 0x1000)
            uc.mem_write(buf + 0xC, bytes([base]))
            _run(uc, 0x49b5d0, buf, {4: val}, {})
            got = uc.mem_read(buf + 0xC, 1)[0]
            want = (base & 0x0F) | ((val & 0x0F) << 4)
            ok &= _t("0x49b5d0 高半字节: 0x%02x|v=%d -> 0x%02x (want 0x%02x)" % (base, val, got, want), got == want)

    # === C. 0x4ab300 自由高半字节集合（确定性：0x4ebd60 强制 0 → 返回最小自由值）===
    for prov in (0, 5, 20, 48):
        for level in (0, 1, 2, 3, 4, 5, 8):
            free = py_ab300_free(level, prov)
            want = min(free) if free else 0
            got = _ab300(level, prov)
            ok &= _t("0x4ab300(level=%d,prov=%d) -> %d (min free=%d)" % (level, prov, got, want),
                     got == want)

    # === D. 0x4ab3c0 端到端：成功行动后 byte[0xc] = (quality<<4)|(level+1) ===
    PROV = 5
    prov_base = KOKU + PROV * KOKU_STRIDE
    actor = 0xB0000
    for L in (0, 1, 2, 3, 4, 5, 8, 9):
        for lordw2 in (13, 16, 695, 0):
            uc = _uc()
            uc.mem_map(actor, 0x1000)
            uc.mem_write(actor + 0x24, bytes([PROV]))   # actor.prov
            uc.mem_write(actor + 0x11, bytes([0]))      # 阈值用 &3=0
            uc.mem_write(prov_base + 0x0, (PROV & 0xFFFF).to_bytes(2, "little"))
            uc.mem_write(prov_base + 0x4, (0 & 0xFFFF).to_bytes(2, "little"))   # lord idx 0
            uc.mem_write(prov_base + 0xC, bytes([L & 0xFF]))
            uc.mem_write(ENT + 0 * ENT_STRIDE + 0x2, (lordw2 & 0xFFFF).to_bytes(2, "little"))  # 实体[0].word[0x2]
            forces = {0x49f5e0: actor, 0x49fd30: 1, 0x4a3560: 0, 0x4ebd60: 0,
                      0x47bfe0: 1, 0x44df20: 0, 0x47b900: 0, 0x47c080: 0, 0x472ea0: 0,
                      0x49c2b0: 0, 0x49c310: 0}
            # 0x4a3560 是 stdcall（清理自身 1 个栈参数），钩子须额外 +4 以平衡栈
            force_argc = {0x4a3560: 1}
            _run(uc, 0x4ab3c0, None, {4: actor}, forces, force_argc)
            newc = uc.mem_read(prov_base + 0xC, 1)[0]
            low = newc & 0xF
            high = (newc >> 4) & 0xF
            want_low = (L + 1) if L < 9 else 0xA
            if L == 9:
                want_high = {13: 2, 16: 1, 695: 1}.get(lordw2, 0)
            elif L + 1 > 4:
                want_high = 0
            else:
                want_high = _ab300(L + 1, PROV)
            ok &= _t("0x4ab3c0 L=%d lordw2=%d -> byte[0xc]=0x%02x (low=%d want %d, high=%d want %d)"
                     % (L, lordw2, newc, low, want_low, high, want_high),
                     low == want_low and high == want_high)

    # === E. 0x4aa820 不写 delta（仅格式化消息）===
    uc = _uc()
    prov = 5
    actor_e = 0xB0000
    other_e = 0xB1000
    protag = 0xB2000
    for p in (actor_e, other_e, protag):
        uc.mem_map(p, 0x1000)
    uc.mem_write(actor_e + 0x24, bytes([prov]))
    uc.mem_write(actor_e + 0x25, bytes([0]))
    uc.mem_write(other_e + 0x24, bytes([prov]))
    uc.mem_write(other_e + 0x25, bytes([0]))
    uc.mem_write(protag + 0x24, bytes([prov]))
    uc.mem_write(protag + 0x0, (0).to_bytes(2, "little"))
    uc.mem_write(prov_base + 0xC, bytes([0x37]))
    forces = {0x49f5e0: protag, 0x47bfe0: 1, 0x47b900: 0, 0x47c080: 0, 0x49c2b0: 0, 0x49c310: 0}
    # 0x4aa820 读 esi=[esp+0x28]、[esp+0x24]；栈：[STACK]=RET,[STACK+4]=other,[STACK+8]=actor
    _run(uc, 0x4aa820, None, {4: other_e, 8: actor_e}, forces)
    after = uc.mem_read(prov_base + 0xC, 1)[0]
    ok &= _t("0x4aa820 不修改 国政治[prov].byte[0xc] (0x37 -> 0x%02x)" % after, after == 0x37)

    # === F. 静态结构断言（与续181呼应）===
    from _dis_helper import disasm
    d3 = " ".join(r["ops"] for r in disasm(0x4ab3c0, 0x180))
    ok &= _t("0x4ab3c0 调 0x49b5b0/0x49b5d0 写 byte[0xc] 两半字节", "49b5b0" in d3 and "49b5d0" in d3)
    ok &= _t("0x4ab3c0 弹关系消息 0xd20/0xd21", "d20" in d3 and "d21" in d3)
    d2 = " ".join(r["ops"] for r in disasm(0x4aa820, 0x140))
    ok &= _t("0x4aa820 格式化关系消息 0x581/0x582 入 0x517710", "581" in d2 and "582" in d2 and "517710" in d2)
    d1 = " ".join(r["ops"] for r in disasm(0x4aa690, 0x191))
    ok &= _t("0x4aa690 调 0x49faf0(国石高) 与 0x4aa820 dispatch", "49faf0" in d1 and "4aa820" in d1)

    print()
    print("结果：" + ("全部通过" if ok else "存在失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
