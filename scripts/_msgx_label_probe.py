#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续171 下一步(B)：给续170 的 3 个 MSG 置信消费函数补事件标签。
通过反汇编每个函数、收集 push 的 MSGX id 常量 + 邻近的 call 目标，
与 msgx_all_texts.json / hexmes_texts.json 交叉比对，给出中文事件标签。
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

import os, re, json
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()

msgx = json.load(open(os.path.join(HERE, "msgx_all_texts.json"), encoding="utf-8"))["texts"]
hexm = json.load(open(os.path.join(HERE, "hexmes_texts.json"), encoding="utf-8"))["texts"]
msgx_keys = set(int(k) for k in msgx.keys())
hexm_keys = set(int(k) for k in hexm.keys())

TARGETS = {
    "0x4a5010": "相性ベース 登用/引抜 A",
    "0x4a5370": "相性ベース 登用/引抜 B·寢返し/離反",
    "0x4d7fe0": "家臣 解雇/追放/離反処理",
}

def dis(va, n):
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.skipdata = True
    off = va - BASE
    return list(md.disasm(bytes(MEM[off:off+n]), va))

def lookup(imm):
    if imm in msgx_keys:
        return ("MSGX", imm, msgx[str(imm)])
    if imm in hexm_keys:
        return ("HEXMES", imm, hexm[str(imm)])
    return None

for va_s, name in TARGETS.items():
    va = int(va_s, 16)
    print("="*70)
    print(f"### {va_s}  {name}")
    code = dis(va, 0x900)
    # 收集 push imm 常量
    pushes = []
    calls = set()
    for ins in code:
        if ins.mnemonic == "push" and ins.op_str.startswith("0x"):
            try:
                imm = int(ins.op_str, 16)
                pushes.append((ins.address, imm))
            except: pass
        if ins.mnemonic == "call":
            calls.add(ins.op_str)
    # 命中 MSGX/HEXMES 的 push
    hits = [(a, i, lookup(i)) for (a, i) in pushes if lookup(i)]
    print(f"  解码指令 {len(code)} 条；push imm {len(pushes)} 个；命中文本 {len(hits)} 个；call 目标 {len(calls)} 个")
    if hits:
        for a, i, info in hits:
            kind, mid, txt = info
            short = txt.replace("\n", " ")[:80]
            print(f"    @0x{a:06x} push {kind} #{mid} : {short}")
    else:
        # 没命中，列出所有 push imm（取小范围，可能是加密/异或后的 msgid）
        small = [(a,i) for (a,i) in pushes if i < 8000]
        print("    无直接 MSGX 命中；前若干 push imm(<8000):")
        for a,i in small[:25]:
            print(f"      @0x{a:06x} push {i} (0x{i:x})")
    # 打印 call 目标（识别 message-display 例程）
    print("    call 目标:", sorted(calls)[:30])
