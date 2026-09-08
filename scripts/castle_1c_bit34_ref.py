#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
castle_1c_bit34_ref.py — 城种 +0x1c bit3/bit4 定名（续251）
================================================================================
承接续250（bit2=重视军备、bit5=築城済）。

| bit | 定名 | 证据 |
|---|---|---|
| bit3 (0x08) | **筑城中** | SET@`0x4b4136/0x4b44e2` 紧邻 MSGX 0xdb2「…就可完工」/0xdc0「立即开始筑城」；门控 `0x4b45c3` |
| bit4 (0x10) | **开垦中** | 门控 `0x4c92d3` 在开垦入口（MSG 0xd85「不能进行开垦」）；`0x4ca0c0` 按主命 idx==4 路由 |

分派器 `0x4ca0c0`：`0x4c9f10` = (`word[0x49f6b0()]!=4`) → bit3，否则 bit4。
主命名表 `0x504b28` idx4 = 开垦农田、idx6 = 筑城。

运行：`python scripts/castle_1c_bit34_ref.py` → RESULT n/n
"""
from __future__ import annotations

import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
BASE = 0x400000
MEM = open(os.path.join(_HERE, "_unpacked_mem.bin"), "rb").read()
TEXTS = json.load(open(os.path.join(_HERE, "msgx_all_texts.json"), encoding="utf-8"))["texts"]
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True
results = []


def chk(name, cond, detail=""):
    results.append((name, bool(cond)))
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", name,
                           (" — " + detail) if detail else ""))


def rd(va, n):
    return MEM[va - BASE:va - BASE + n]


def dis(va, n=0x40):
    return " | ".join("%s %s" % (i.mnemonic, i.op_str)
                      for i in md.disasm(rd(va, n), va))


def callers(target):
    out = []
    for i in range(len(MEM) - 5):
        if MEM[i] != 0xE8:
            continue
        rel = int.from_bytes(MEM[i + 1:i + 5], "little", signed=True)
        if BASE + i + 5 + rel == target:
            out.append(BASE + i)
    return out


print("=== A. bit3 SET <-> 筑城 MSG ===")
chk("A1 0x4b4136 call 0x49aba0", 0x4B4136 in callers(0x49ABA0))
chk("A2 同函数 push MSG 0xdb2", b"\x68\xb2\x0d\x00\x00" in rd(0x4B4120, 0x20))
chk("A3 MSG 0xdb2 含「完工」", "完工" in TEXTS.get("3506", ""))
chk("A4 0x4b44e2 call 0x49aba0 前有 0xdc0「开始筑城」",
    0x4B44E2 in callers(0x49ABA0) and "筑城" in TEXTS.get("3520", ""))
chk("A5 门控 0x4b45c3 test [esi+0x1c],8",
    rd(0x4B45C3, 4) == bytes([0xF6, 0x46, 0x1C, 0x08]))

print("\n=== B. bit4 <-> 开垦 ===")
chk("B1 门控 0x4c92d3 test [ebp+0x1c],0x10",
    rd(0x4C92D3, 4) == bytes([0xF6, 0x45, 0x1C, 0x10]))
chk("B2 同函数含开垦子系统 MSG 0xd9d/作业进展",
    b"\x68\x9d\x0d\x00\x00" in rd(0x4C9280, 0x120))
chk("B2b 开垦成功文案 0xd96 含「开垦」", "开垦" in TEXTS.get(str(0xD96), ""))
chk("B3 bit4 置位时 MSG 0x16e8（作业已结束）",
    b"\x68\xe8\x16\x00\x00" in rd(0x4C92D3, 0x20)
    and "作业" in TEXTS.get(str(0x16E8), ""))

print("\n=== C. 分派器 0x4ca0c0: idx==4 -> bit4, else bit3 ===")
chk("C1 0x4c9f10 cmp word[eax],4 + setne",
    "0x4" in dis(0x4C9F10, 0x20) and "setne" in dis(0x4C9F10, 0x20))
body = rd(0x4CA0C0, 0x30)
chk("C2 0x4ca0c0 调 0x4c9f10 后分支 bit3/bit4 setter",
    b"\xe8" in body[:8]
    and 0x4CA0D2 in callers(0x49ABA0)
    and 0x4CA0E1 in callers(0x49ABC0))
# 主命名表 idx4
# 0x504b28 is pointer table — read ptr[4]
ptr4 = struct.unpack_from("<I", MEM, 0x504B28 - BASE + 4 * 4)[0]
name4 = MEM[ptr4 - BASE:ptr4 - BASE + 16].split(b"\x00")[0].decode("gbk", "replace")
chk("C3 主命表 idx4 = 开垦农田", "开垦" in name4, name4)
ptr6 = struct.unpack_from("<I", MEM, 0x504B28 - BASE + 4 * 6)[0]
name6 = MEM[ptr6 - BASE:ptr6 - BASE + 16].split(b"\x00")[0].decode("gbk", "replace")
chk("C4 主命表 idx6 = 筑城", "筑城" in name6, name6)

passed = sum(1 for _, c in results if c)
total = len(results)
print("\nRESULT: %d/%d checks passed" % (passed, total))
raise SystemExit(0 if passed == total else 1)
