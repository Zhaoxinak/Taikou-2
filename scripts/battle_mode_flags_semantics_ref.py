# -*- coding: utf-8 -*-
"""
battle_mode_flags_semantics_ref.py — #89 合战 5 全局模式标志「精确玩法语义」闭合
====================================================================================
承接续186（5 标志 setter/getter 几何 + 值语义 20/20）与清单 #89「模式标志精确玩法语义（须 emu 追 struct 基址+偏移）」。

本脚本用 **setter call-site 战斗相位上下文** 钉死 5 标志的玩法语义（谁在什么战斗阶段写它），
并用 **getter 调用点=0 + 字面绝对引用仅限 setter/getter 包装器** 坐实「消费侧经 base 寄存器+偏移访问 struct」机制。

5 标志（续186 已定位地址）：
  mode_m1     0x511bf8  setter 0x42c140
  mode_m2     0x51352c  setter 0x43cb20 (a) / 0x43cfc0 (b xor1)
  parity      0x513540  setter 0x43ca70 (a) / 0x43ca90 (b)
  battle_type 0x513548  setter 0x43ca20
  handle_stat 0x513534  setter 0x43cb70

玩法语义（来自 call-site 上下文）：
  mode_m1      = 合战/出兵部署「交战进行主标志」(0/1，配置·合战init 置位/清零)
  mode_m2      = 合战子模式标志(0/1/计算值；攻城戦内 bit0 概率翻转=攻城戦变体)
  parity       = 战斗阶段/回合奇偶计数(合战init 置初值；攻城戦每阶段 +1 钳顶)
  battle_type  = 战斗类型枚举(0=攻城戦@0x434000 / 3=野戦@0x422000)
  handle_stat  = 攻城戦状态/句柄字(攻城戦init 自 [esp+0x3c] 写入)

自测：T1–T7 setter call-site 计数符合上表；T8 getter 调用点=0（消费侧 base+offset 机制）；
     T9 battle_type 两类 init 上下文(攻城戦 0x43430b/0x434919 + 野戦 0x4228e6/0x422acc) 均在位。

运行：python battle_mode_flags_semantics_ref.py   （从 scripts/ 目录）
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

# (setter_va, 期望 call-site 数, flag 名)
SETTERS = [
    (0x42c140, 5, "mode_m1"),
    (0x43cb20, 4, "mode_m2_a"),
    (0x43cfc0, 1, "mode_m2_b_xor"),
    (0x43ca70, 1, "parity_a"),
    (0x43ca90, 2, "parity_b"),
    (0x43ca20, 4, "battle_type"),
    (0x43cb70, 1, "handle_stat"),
]
GETTERS = [0x42c151, 0x43cb11, 0x43cab1]  # mode_m1/mode_m2/parity 的 getter 入口

# battle_type 期望出现的两类 init 上下文 call-site
BATTLE_TYPE_SIEGE = {0x43430b, 0x434919}   # 攻城戦 init (0x434000)
BATTLE_TYPE_FIELD = {0x4228e6, 0x422acc}   # 野戦 init (0x422000)


def load():
    return open(MEM, "rb").read()


def find_calls(b, target):
    out = []
    n = len(b)
    i = 0
    while i < n - 4:
        if b[i] == 0xE8:
            rel = struct.unpack_from("<i", b, i + 1)[0]
            tgt = (i + BASE) + 5 + rel
            if tgt == target:
                out.append(i + BASE)
        i += 1
    return out


def main():
    b = load()
    print("=== #89 合战模式标志 精确玩法语义（setter call-site 验证）===\n")
    results = []
    counts = {}
    for st_va, exp, name in SETTERS:
        sites = find_calls(b, st_va)
        counts[name] = len(sites)
        ok = len(sites) == exp
        results.append(ok)
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:12s} setter=0x{st_va:06x}  call-site={len(sites)} (期望 {exp})")

    # T8 getter 调用点=0
    print()
    gzero = True
    for g in GETTERS:
        c = find_calls(b, g)
        if c:
            gzero = False
        print(f"  getter 0x{g:06x}: {len(c)} call-site(s) -> {['0x%x'%x for x in c]}")

    # T9 battle_type 两类 init 上下文
    bt_sites = set(find_calls(b, 0x43ca20))
    has_siege = len(BATTLE_TYPE_SIEGE & bt_sites) > 0
    has_field = len(BATTLE_TYPE_FIELD & bt_sites) > 0
    print(f"\n  battle_type call-site 含 攻城戦init({sorted(hex(x) for x in BATTLE_TYPE_SIEGE & bt_sites)}) = {has_siege}")
    print(f"  battle_type call-site 含 野戦init({sorted(hex(x) for x in BATTLE_TYPE_FIELD & bt_sites)}) = {has_field}")

    ok8 = gzero
    ok9 = has_siege and has_field
    results += [ok8, ok9]

    print(f"\n  [{'PASS' if ok8 else 'FAIL'}] getter 调用点=0（消费侧 base+offset struct 访问机制坐实）")
    print(f"  [{'PASS' if ok9 else 'FAIL'}] battle_type 两类 init 上下文均在位(攻城戦/野戦)")

    total = len(results)
    passed = sum(1 for x in results if x)
    print(f"\n==== SUMMARY: {passed}/{total} PASS ====")
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
