#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
续253 — 评价词档位阈值 + 绘制器静态全闭（推翻「须 emu / 0x4d0e10 / 0x47ca70」旧残留）

背景
----
续117 已用语义+排他闭 8↔10 绑定，但仍标「绘制循环 0x47ca70 行序 / 阈值须 emu，
阈值散见 0x4d0e10」。本轮证明：

  1) 0x4d0e80/f20/fa0 的 cmp 1000/2000/3000/40/55/60/80 是 **MSG 台词分派**
     （查字表 0x50ce78..），**不是**评价词阈值。
  2) 0x47ca70 是城池面板 **字段名标签** 布局（续87 已证），不读 0x50b6ba。
  3) 真实消费者 = 9 段 thiscall 绘制簇（入口 0x497a30），经
       lea reg, [tier + tier*8 + group_disp]
     访问评价词表（stride 9；disp = 组基 - 2，因槽前 2 空格）。
  4) 档位公式（全段同一 sbb 惯用形）：
       val < lo → 0； lo ≤ val < hi → 1； val ≥ hi → 2
       （jae lo; xor=0 / cmp hi; sbb; add 2）

自测：映像字节级核对 9 段阈值立即数 + lea 位移 + 三档 GBK 词 + 双轴 G5。
"""
from __future__ import annotations

import os
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(_ROOT, "scripts", "_unpacked_mem.bin")
BASE = 0x400000

# (name, field, lea_va, disp, lo, hi, lo_enc_off_from_lea, notes)
# lo/hi are the cmp immediates; encoding verified at fixed offsets in each stub.
ENTRIES = [
    # G0 军资金: lea@0x49798d disp 0x50b6b8; cmp 0x3e8 / 0x2710 on [ebp+6]
    ("G0_资金", "军资金", 0x49798D, 0x50B6B8, 1000, 10000, ("缺乏", "丰富", "富强")),
    # G1 支持率: lea@0x4980b2; 50/80 via getter 0x49bde0
    ("G1_支持", "支持率", 0x4980B2, 0x50B6D3, 50, 80, ("低", "普通", "高")),
    # G2 军粮: lea@0x497b27; 1000/10000 on [ebp+8]
    ("G2_军粮", "军粮", 0x497B27, 0x50B6EE, 1000, 10000, ("缺乏", "足够", "充裕")),
    # G3 防御: lea@0x4981ec; 50/150 on byte[ebp+0xc]
    ("G3_防御", "防御度", 0x4981EC, 0x50B709, 50, 150, ("薄弱", "普通", "坚固")),
    # G4 士兵: lea@0x497c40; 3000/15000 on [ebp+0xa]
    ("G4_士兵", "士兵数", 0x497C40, 0x50B724, 3000, 15000, ("缺乏", "充实", "强大")),
    # G5a 军马: lea@0x497d70; 2000/10000 via 0x49bdf0 = word[ecx+2]
    ("G5a_军马", "军马", 0x497D70, 0x50B73F, 2000, 10000, ("缺少", "丰富", "无数")),
    # G5b 洋枪: lea@0x497ea0; same words/thresholds via 0x49be00 = word[ecx+4]
    ("G5b_洋枪", "洋枪", 0x497EA0, 0x50B73F, 2000, 10000, ("缺少", "丰富", "无数")),
    # G6 训练: lea@0x4982eb; 70/150 on byte[ebp+0xd]
    ("G6_训练", "训练度", 0x4982EB, 0x50B75A, 70, 150, ("稚嫩", "普通", "精干")),
    # G7 士气: lea@0x4983ef; 70/150 on byte[ebp+0xe]
    ("G7_士气", "士气", 0x4983EF, 0x50B775, 70, 150, ("低", "精神", "勇敢")),
]


def _load():
    with open(IMG, "rb") as f:
        return f.read()


def _u32(mem, va):
    return struct.unpack_from("<I", mem, va - BASE)[0]


def _u16(mem, va):
    return struct.unpack_from("<H", mem, va - BASE)[0]


def _decode_slot(mem, va):
    raw = mem[va - BASE : va - BASE + 9]
    # strip spaces / NULs
    s = raw.split(b"\x00")[0].decode("gbk", "ignore")
    return "".join(ch for ch in s if "\u4e00" <= ch <= "\u9fff")


def tier(val, lo, hi):
    if val < lo:
        return 0
    if val < hi:
        return 1
    return 2


def main():
    mem = _load()
    checks = 0
    passed = 0

    def chk(name, cond):
        nonlocal checks, passed
        checks += 1
        if cond:
            passed += 1
        print(f"  [{'OK' if cond else 'FAIL'}] {name}")

    # Entry exists
    chk("entry 0x497a30 prologue", mem[0x497A30 - BASE : 0x497A30 - BASE + 4] == bytes([0x53, 0x55, 0x8B, 0x6C]))

    # Misattribution: 0x4d0e80 calls into MSG helper 0x4d0f00, not eval lea
    chk("0x4d0e80 not eval (has call 4d0f00)", mem[0x4D0E9B - BASE] == 0xE8)

    for name, field, lea_va, disp, lo, hi, words in ENTRIES:
        # lea displacement dword at lea_va+3 (8D xx sib disp32)
        got_disp = _u32(mem, lea_va + 3)
        chk(f"{name} lea disp={disp:#x}", got_disp == disp)

        # three tier strings
        for t, w in enumerate(words):
            got = _decode_slot(mem, disp + t * 9)
            chk(f"{name} tier{t}={w}", got == w)

        # find cmp imm16 for lo/hi in the 0x40 bytes before lea
        window = mem[lea_va - BASE - 0x40 : lea_va - BASE]
        lo_pat = b"\x66\x3d" + struct.pack("<H", lo)
        hi_pat = b"\x66\x3d" + struct.pack("<H", hi)
        chk(f"{name} cmp lo={lo}", lo_pat in window)
        chk(f"{name} cmp hi={hi}", hi_pat in window)

        # sbb tier idiom present
        chk(f"{name} sbb idiom", b"\x1b\xf6\x83\xc6\x02" in window or b"\x19\xf6\x83\xc6\x02" in window)

        # formula smoke
        chk(f"{name} tier(lo-1)=0", tier(lo - 1, lo, hi) == 0)
        chk(f"{name} tier(lo)=1", tier(lo, lo, hi) == 1)
        chk(f"{name} tier(hi-1)=1", tier(hi - 1, lo, hi) == 1)
        chk(f"{name} tier(hi)=2", tier(hi, lo, hi) == 2)

    # G5 dual-axis: same disp
    chk("G5a/G5b share disp", ENTRIES[5][3] == ENTRIES[6][3])

    # getters
    chk("0x49bde0 = movzx ax,[ecx+1]", mem[0x49BDE0 - BASE : 0x49BDE0 - BASE + 6] == bytes([0x66, 0x0F, 0xB6, 0x41, 0x01, 0xC3]))
    chk("0x49bdf0 = mov ax,[ecx+2]", mem[0x49BDF0 - BASE : 0x49BDF0 - BASE + 4] == bytes([0x66, 0x8B, 0x41, 0x02]))
    chk("0x49be00 = mov ax,[ecx+4]", mem[0x49BE00 - BASE : 0x49BE00 - BASE + 4] == bytes([0x66, 0x8B, 0x41, 0x04]))

    print(f"RESULT: {passed}/{checks} checks passed")
    return 0 if passed == checks else 1


if __name__ == "__main__":
    sys.exit(main())
