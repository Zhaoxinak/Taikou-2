#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
太阁立志传2 · 计略「谣言 Rumor」时间-空间落地模式 参考实现

来源：脱壳映像 scripts/_unpacked_mem.bin 静态段 dump + 反汇编 + Unicorn 2.1.4 实证
      (续15、续38、scripts/_emu_rumor_land.py)。

涉及原版函数链
--------------
0x436190   Rumor handler          (cdecl, 两 corps 指针)
  └─ 0x435d60 effect_dispatch
       └─ 0x435280 shared_prim    (播消息 0xac)
            └─ 0x43cf10(目标)     落地核心 — 4 轮编辑
            └─ 循环 5× `0x43dc20(目标, i, 4)` 对 5 个单位槽各走一次

0x438c60(0x5133d0, P, byte[P], byte[P+2], 0, 0)  通用「单格部署/单位编辑」原语
0x4a0c60(byte[0x5037b0 + k])                      「递减延时循环」(6/4/2/1)

时间-空间模式 (2026-08-28 续40 精化,纠正续15/续38 「9 个部署格」)
=============================================================
原续15/续38 表述「单条谣言对 9 个部署格施加编辑(4×2 + 1)」,这是
对「0x43cf10 调用 0x438c60 9 次」的字面解读,但忽略了:
  1. P = 同一单位槽(由 0x43dc20 的 i 决定)
  2. 9 次都写同一格 P,只是参数 (b0,b2) 与 (b2,b0) 互换 + 收尾
  3. 但 0x435280 在谣言链外层「循环 5× 0x43dc20」 → 5 个单位槽各跑一次

⇒ 单条谣言实际写块次数:
   = 5 单位槽 × (4 轮 × 2 编辑 + 1 收尾)
   = 5 × 9 = 45 次 0x438c60 调用
   但每次都是对同一单位的字段反复编辑(token 翻转 + 数值缓冲 ±4),
   而不是「9 个不同部署格」。

延时动画: 0x5037b0 = [6, 4, 2, 1]
  每轮编辑后调 0x4a0c60(k=0..3),延时计数递减(6→4→2→1 帧)。
  ⇒ 「谣言扩散」= 视觉延时,不是真的传播到其他格。

arg5 全程 = 0 ⇒ 走左军分支(0x438fa0 验证 token ∈ {'/','1','7','9'}):
  DEPLOY[esi] += 0xfc(≡−4)   →  '9'→'5'/'1'→'-'/'7'→'3'/'/'→'+'
  byte[0x512b88+esi] += 0xfc → UBUF_A 减少 4
  byte[0x512b89+esi] += 0xfc → UBUF_B 减少 4

⇒ 谣言落地语义精化:
  - 「兵变/倒戈」= 5 单位槽逐个「换边 + 实力 −4」
  - 「9 次落地」= 单单位内 9 次写(token 翻 + 缓冲 + 收尾),非 9 格
  - 「6/4/2/1 延时」= 视觉扩散动画
  - 「arg5==0」= 全程左军 →4;若要测右军 →4,看其他计略 handler
"""

import os
import json
from typing import List

BASE = 0x400000
_HERE = os.path.dirname(os.path.abspath(__file__))
_TACTIC_JSON = os.path.join(_HERE, "tactic_tables.json")

# 0x5037b0 延时计数(rumor_mods)
RUMOR_MODS = [6, 4, 2, 1]

# 0x43cf10 循环 4 轮 × 2 编辑 = 8 + 末次 1 = 9 次/单位
CALLS_PER_UNIT = 9

# 0x435280 循环 5 单位槽
CALLS_PER_RUMOR = 5 * CALLS_PER_UNIT  # = 45

# 左军 token(0x438fa0 验证集)
LEFT_TOKENS = {'/', '1', '7', '9'}
# 右军 token(0x438fc0 验证集)
RIGHT_TOKENS = {'+', '-', '3', '5'}

# 左军 token + 0xfc(−4) = 右军 token
LEFT_TO_RIGHT = {'/': '+', '1': '-', '7': '3', '9': '5'}
# 右军 token + 0x04(+4) = 左军 token
RIGHT_TO_LEFT = {v: k for k, v in LEFT_TO_RIGHT.items()}


def rumor_calls_per_rumor() -> int:
    """单条谣言总落地次数 = 5 单位槽 × 9 次/单位 = 45 次 0x438c60 调用。"""
    return CALLS_PER_RUMOR


def rumor_calls_per_unit() -> int:
    """单单位 0x438c60 调用次数 = 4 轮 × 2 编辑 + 1 收尾 = 9。"""
    return CALLS_PER_UNIT


def rumor_animation_frames() -> int:
    """4 轮延时累计:6+4+2+1=13 帧(伪扩散动画)。"""
    return sum(RUMOR_MODS)


def rumor_swap_token(tok: str, side: str = "left") -> str:
    """根据 side 把 token 翻到对方。
    side='left'  → 0xfc(−4) 左军 token 翻为右军
    side='right' → 0x04(+4) 右军 token 翻为左军
    """
    if side == "left":
        if tok in LEFT_TO_RIGHT:
            return LEFT_TO_RIGHT[tok]
        return tok  # 非左军 token,不翻
    elif side == "right":
        if tok in RIGHT_TO_LEFT:
            return RIGHT_TO_LEFT[tok]
        return tok
    return tok


# ============================================================ 自检
def _selftest():
    PASS = FAIL = 0
    def chk(name, cond, detail=''):
        nonlocal PASS, FAIL
        if cond: PASS += 1; print(f"  PASS  {name}" + (f"  ({detail})" if detail else ''))
        else:    FAIL += 1; print(f"  FAIL  {name}" + (f"  ({detail})" if detail else ''))

    print("=== 时间-空间精化 ===")
    chk("单单位 9 次(4×2 + 1 收尾)", rumor_calls_per_unit() == 9, str(rumor_calls_per_unit()))
    chk("单条谣言 45 次(5 单位 × 9)", rumor_calls_per_rumor() == 45, str(rumor_calls_per_rumor()))
    chk("动画延时累计 13 帧", rumor_animation_frames() == 13, str(rumor_animation_frames()))
    chk("延时表 [6,4,2,1] 单调递减", RUMOR_MODS == sorted(RUMOR_MODS, reverse=True))

    print("\n=== Token 翻转映射(±4)===")
    chk("'/' + (-4) = '+'", rumor_swap_token('/', 'left') == '+')
    chk("'1' + (-4) = '-'", rumor_swap_token('1', 'left') == '-')
    chk("'7' + (-4) = '3'", rumor_swap_token('7', 'left') == '3')
    chk("'9' + (-4) = '5'", rumor_swap_token('9', 'left') == '5')
    chk("'+' + (+4) = '/'", rumor_swap_token('+', 'right') == '/')
    chk("'-' + (+4) = '1'", rumor_swap_token('-', 'right') == '1')
    chk("'3' + (+4) = '7'", rumor_swap_token('3', 'right') == '7')
    chk("'5' + (+4) = '9'", rumor_swap_token('5', 'right') == '9')

    print("\n=== 验证集 ===")
    chk("左军 token 4 个", LEFT_TOKENS == {'/', '1', '7', '9'})
    chk("右军 token 4 个", RIGHT_TOKENS == {'+', '-', '3', '5'})
    chk("左+右 = 8 个不重复", len(LEFT_TOKENS | RIGHT_TOKENS) == 8)
    chk("左∩右 = ∅", len(LEFT_TOKENS & RIGHT_TOKENS) == 0)

    print("\n=== 反向自检:对每条谣言时间线展开 ===")
    # 谣言 5 单位 × 9 编辑,共 45 次
    total = 0
    timeline = []
    for slot in range(5):
        for k in range(4):
            timeline.append((slot, k, 'main',  RUMOR_MODS[k]))
            timeline.append((slot, k, 'swap',  RUMOR_MODS[k]))
        timeline.append((slot, 4, 'close', 0))
    total = len(timeline)
    chk("timeline 长度 = 45", total == 45, str(total))
    chk("slot 0..4 各 9 次", [t[0] for t in timeline].count(0) == 9)
    chk("main + swap = 8×5 = 40", sum(1 for t in timeline if t[2] in ('main','swap')) == 40)
    chk("close = 5", sum(1 for t in timeline if t[2] == 'close') == 5)

    # 累积延时(main + swap 各调一次 0x4a0c60 → 每轮 2×13,5 单位 → 130)
    cum = sum(t[3] for t in timeline)
    chk("累积延时 = 5×2×(6+4+2+1) = 130 帧", cum == 130, str(cum))
    print(f"  [info] 真实延时:main+swap 各一次 0x4a0c60 → 2×13/轮 ×5 slot = {cum} 帧")

    print(f"\n{PASS} PASS / {FAIL} FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    rc = _selftest()
    raise SystemExit(rc)
