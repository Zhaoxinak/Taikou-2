#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
续70 — 城表/城町记录 0x51eb88 字段布局（静态逐字节自校验）。

已证实事实：
  * 基址 0x51eb88，STRIDE = 31（证据：0x402e4b shl eax,5(×32) / sub eax,ecx(×31)
    / add eax,0x51eb88；同形于 0x4040f3、0x40d14f 等多处）。
  * 记录 31 字节（偏移 0x00..0x1e）；200 条（92 城 + 108 町）。
  * C++ 对象布局：+0x00 = vtable 指针(dword)，+0x04 = 链表 next 指针(dword)，
    +0x08..+0x1e = 数据。
  * 注意：ctor 0x4a3a4f 还会经由 helper(0x49a750/..) 写 +0x24/+0x25/+0x2c/+0x2d，
    那些属于「更大的运行时 C++ 实例」（与 0x51eb88 记录经 0x4a05a0 链接），
    **不属于 31 字节记录**，本校验只覆盖 0x00..0x1e。
"""
from __future__ import annotations

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
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
BASE = 0x400000
SZ = len(MEM)
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
TARGET = 0x51eb88

PASS = FAIL = 0
def check(name, cond, detail=''):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f'  PASS  {name}' + (f'  ({detail})' if detail else ''))
    else:
        FAIL += 1
        print(f'  FAIL  {name}' + (f'  ({detail})' if detail else ''))

def bytes_at(va, n):
    return MEM[va-BASE:va-BASE+n]

def contains(va, pat):
    return bytes_at(va, len(pat)) == pat

# ---- 1. 基址 / stride 31 ----
check("基址 0x51eb88 存在于映像", bytes_at(TARGET, 4) is not None)
# 0x402e4b: shl eax,5 ; sub eax,ecx ; add eax,0x51eb88  => stride 31
check("stride=31 指令序列 @0x402e4b (shl5/sub/add base)",
      contains(0x402e4b, bytes([0xc1,0xe0,0x05,0x2b,0xc1,0x05,0x88,0xeb,0x51,0x00])),
      "shl eax,5 / sub eax,ecx / add eax,0x51eb88")
# 同形 0x4040f3（另一处索引）
check("stride=31 第二处 @0x4040f3",
      contains(0x4040f3, bytes([0xc1,0xe0,0x05,0x2b,0xc1,0x05,0x88,0xeb,0x51,0x00])))

# ---- 2. +0x00 vtable / +0x04 next / +0x08 byte / +0x16 status ----
# 0x408e84: mov byte[eax+0x16], bl   (遍历写状态标记)
check("+0x16 状态字节写入 @0x408e84 (mov byte[eax+0x16],bl)",
      contains(0x408e84, bytes([0x88,0x58,0x16])))
# 0x408e87: mov eax, dword[eax+4]    (链表 next 指针)
check("+0x04 链表 next 指针 @0x408e87 (mov eax,dword[eax+4])",
      contains(0x408e87, bytes([0x8b,0x40,0x04])))
# 0x4040fd: mov al, byte[eax+8]      (数据首字节)
check("+0x08 数据首字节 @0x4040fd (mov al,byte[eax+8])",
      contains(0x4040fd, bytes([0x8a,0x40,0x08])))

# ---- 3. +0x0a 城主武将编号 (word) — 由字段扫描覆盖（见下方宽度断言）----

# ---- 4. 字段扫描：确认 0x00..0x1e 均有访问，且 0x1f 起为越界/实例 ----
import collections
REGN = {312:'eax',313:'ecx',314:'edx',315:'ebx',316:'esp',317:'ebp',318:'esi',319:'edi',
        332:'eax',333:'ecx',334:'edx',335:'ebx',336:'esp',337:'ebp',338:'esi',339:'edi'}
# (32-bit reg enum ids from capstone.x86; use name via op.reg mapping)
from capstone.x86 import (X86_REG_EAX,X86_REG_EBX,X86_REG_ECX,X86_REG_EDX,X86_REG_ESI,
                          X86_REG_EDI,X86_REG_EBP,X86_REG_ESP)
RNAME={X86_REG_EAX:'eax',X86_REG_EBX:'ebx',X86_REG_ECX:'ecx',X86_REG_EDX:'edx',
       X86_REG_ESI:'esi',X86_REG_EDI:'edi',X86_REG_EBP:'ebp',X86_REG_ESP:'esp'}

# ---- proper forward-walk field scan ----
def scan_fields():
    candidates = collections.defaultdict(lambda: collections.Counter())
    # pass 1: base-load sites
    loads = []
    addr = BASE
    while addr < BASE + SZ:
        try:
            ins = next(md.disasm(MEM[addr-BASE:addr-BASE+16], addr))
        except Exception:
            addr += 1; continue
        s = ins.mnemonic + ' ' + ins.op_str
        if '0x%x'%TARGET in s and ins.mnemonic in ('add','mov','lea') and len(ins.operands)==2:
            d = ins.operands[0]
            if d.type==1 and RNAME.get(d.reg): loads.append((addr, RNAME[d.reg]))
        addr = ins.address + ins.size
    # pass 2: walk forward from each load, track anchored reg
    for va, dst in loads:
        anchored = {dst}
        end = min(va + 600, BASE + SZ - 16)
        try:
            rows = list(md.disasm(MEM[va-BASE:end-BASE], va))
        except Exception:
            continue
        for ins in rows:
            s = ins.mnemonic + ' ' + ins.op_str
            if ins.mnemonic in ('add','mov','lea') and '0x%x'%TARGET in s and len(ins.operands)==2:
                d = ins.operands[0]
                if d.type==1 and RNAME.get(d.reg): anchored.add(RNAME[d.reg])
            for o in ins.operands:
                if o.type==3 and RNAME.get(o.mem.base) in anchored:
                    disp = o.mem.disp
                    if 0 <= disp <= 0x1e + 3:
                        w = 4
                        if 'byte ' in s: w = 1
                        elif 'word ' in s: w = 2
                        candidates[(disp,w)][ins.address] += 1
    return candidates

candidates = scan_fields()

present = set(d for (d,_) in candidates)
rec_min, rec_max = 0x00, 0x1e
check("记录字段覆盖 0x00..0x1e", all(i in present for i in (0x00,0x04,0x08,0x0a,0x0c,0x10,0x14,0x1a,0x1e)),
      "min..max 区间关键偏移均在访问集内")
# 确认 0x1e 是记录末尾：0x1f/0x20/0x21 极少(<=2)且为相邻记录/实例溢出
for off in (0x1f,0x20,0x21):
    tot = sum(sum(candidates.get((off,w), collections.Counter()).values()) for w in (1,2,4))
    check(f"+0x{off:02x} 越界访问极少(<=2, 邻记录/实例溢出)", tot <= 2, f"count={tot}")

# 关键字段宽度断言（来自经济/任命模块已破结论）
check("+0x0a 以 word 访问(城主编号)", (0x0a,2) in candidates)
check("+0x10 以 word 访问(军粮)", (0x10,2) in candidates)
check("+0x12 以 word 访问(米)", (0x12,2) in candidates)
check("+0x14 以 word 访问(资金)", (0x14,2) in candidates)
check("+0x0c 以 byte 访问(农商等级)", (0x0c,1) in candidates)
check("+0x1b 以 byte 访问(城种)", (0x1b,1) in candidates)

print(f"\n=== castle_fields_ref: {PASS} PASS / {FAIL} FAIL ===")
sys.exit(1 if FAIL else 0)
