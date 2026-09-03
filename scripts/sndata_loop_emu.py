#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续227-下一步(B) 实证(确定性部分):
逐 id 跑 0x462fd0 的循环, 捕获 (count=esi, maxclass=ebx, name-base 数组, counter 数组).
门控: byte[0x516638]=0 (class1 开), entity.0x2c=0x0700 (class2 开) -> 最大有效类数.
同时读取 0x47be94 的 14 项跳转表 (key-0x82e -> handler) 与各类 handler 设定的 class.
"""
import struct
from collections import Counter
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_PROT_ALL, UC_HOOK_CODE
from unicorn.x86_const import (
    UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_ESP, UC_X86_REG_ECX,
)

BASE = 0x400000
IMG  = r"F:\Games\Taikou 2\scripts\_unpacked_mem.bin"
with open(IMG, "rb") as f:
    MEM = f.read()

# ---- 读取跳转表 0x47be94 (14 dword) ----
jt_off = 0x47be94 - BASE
jt = struct.unpack("<14I", MEM[jt_off:jt_off+56])
# handler -> class 值
handler_class = {}
# 已知 handler 地址与 class 设定:
# 0x47be6f: or esi,0xffffffff -> -1
# 0x47be5a: mov esi,edi -> edi = arg0 = count
# 0x47be5e: mov esi,1 (然后 inc x10 -> 11)
# 0x47be72: 出口(mov ax,si)
# 0x47be8a: 出口(ax=0xffff)
# 其余 handler 地址需反推: 表项指向这些地址.
def class_for_handler(h):
    if h == 0x47be6f:
        return -1
    if h == 0x47be5a:
        return "count"   # esi=edi=arg0
    if h == 0x47be5e:
        return 1         # 实际 1 然后 inc*10 -> 11
    if h == 0x47be8a:
        return -2        # invalid -> ax=0xffff
    # 其它: 多数 handler 是 0x47be5e 的 fallthrough 链 (inc esi) 或 0x47be6f
    return "?"

print("jump table (key = 0x82e + idx):")
keymap = {}
for i, h in enumerate(jt):
    key = 0x82e + i
    c = class_for_handler(h)
    keymap[key] = (h, c)
    print(f"  idx{i:2d} key=0x{key:x} -> handler=0x{h:x} class={c}")

# ---- emu 逐 id 跑 0x462fd0 循环 ----
REC_BUF = 0x600000
ENT_BUF = 0x600004
HEAP    = 0x630000
STACK   = 0xC00000

mu = Uc(UC_ARCH_X86, UC_MODE_32)
mu.mem_map(BASE, len(MEM), UC_PROT_ALL)
mu.mem_map(REC_BUF & 0xFFFF0000, 0x20000, UC_PROT_ALL)
mu.mem_map(HEAP, 0x10000, UC_PROT_ALL)
mu.mem_map(STACK, 0x10000, UC_PROT_ALL)
mu.mem_write(BASE, MEM)

mu.mem_write(0x49f6b0, b"\xb8" + struct.pack("<I", REC_BUF) + b"\xc3")  # record getter
mu.mem_write(0x49f5e0, b"\xb8" + struct.pack("<I", ENT_BUF) + b"\xc3")  # entity getter
mu.mem_write(0x47bed0, b"\xc3")  # 派发器 no-op (我们只取循环结果)

mu.mem_write(0x516638, b"\x00")                  # class1 gate open
mu.mem_write(ENT_BUF + 0x2c, struct.pack("<H", 0x0700))  # entity.0x2c>>8&7 = 7

captured = {}
def hook_loop(mu, address, size, data):
    # 0x46308e = 循环结束后、call 0x47bed0 之前
    if address == 0x46308e:
        esi = mu.reg_read(UC_X86_REG_ESI)   # count
        ebx = mu.reg_read(UC_X86_REG_EBX)   # max class idx (0..5)
        esp = mu.reg_read(UC_X86_REG_ESP)
        # name bases at [esp+0x24 + k*4], counters at [esp+0x18 + k*2]
        nb = []
        cc = []
        for k in range(esi):
            v = struct.unpack("<I", mu.mem_read(esp + 0x24 + k*4, 4))[0]
            nb.append(v)
            c = struct.unpack("<H", mu.mem_read(esp + 0x18 + k*2, 2))[0]
            cc.append(c)
        captured['last'] = (esi, ebx, nb, cc)

mu.hook_add(UC_HOOK_CODE, hook_loop)

def run_one(idw):
    captured.pop('last', None)
    mu.mem_write(REC_BUF, struct.pack("<H", idw & 0xffff))
    esp = STACK + 0x8000
    mu.reg_write(UC_X86_REG_ESP, esp)
    # 设置返回地址槽: 原函数 ret 会弹 [orig_esp]; 我们让 orig_esp 处=0x4630b2(直到地址)
    mu.mem_write(esp, struct.pack("<I", 0x4630b2))
    try:
        mu.emu_start(0x462fd0, 0x4630b2, count=200000)
    except Exception as e:
        return ("ERR", str(e)[:50])
    if 'last' not in captured:
        return ("NOHOOK", None)
    return captured['last']

print("\n逐 id 循环结果 (gates open):")
print(f"{'id':>4} {'count':>5} {'maxcls':>6}  namebases")
summary = Counter()
for idw in range(0, 215):
    r = run_one(idw)
    if isinstance(r, tuple) and r[0] in ("ERR","NOHOOK"):
        print(f"{idw:>4} {str(r):>20}")
        continue
    esi, ebx, nb, cc = r
    tag = (esi, tuple(nb))
    summary[tag] += 1
    if idw in (0,1,2,3,9,10,200,214):
        print(f"{idw:>4} {esi:>5} {ebx:>6}  {[hex(x) for x in nb]}")

print("\n唯一 (count, namebase-set) 组合数:", len(summary))
for k,v in sorted(summary.items(), key=lambda x:-x[1])[:12]:
    esi, nb = k
    print(f"  count={esi} nb={[hex(x) for x in nb]}  x{v}")
