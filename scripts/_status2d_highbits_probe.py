# -*- coding: utf-8 -*-

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
# _status2d_highbits_probe.py v2 — +0x2d 高字节 F4(0x10)/F2B(0x60) 的消费者 + setter 调用参数追踪
import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

def off(v): return v - BASE
def dis(va, n): return list(md.disasm(MEM[off(va):off(va)+n], va))

def reg_name(o):
    try: return md.reg_name(o.reg)
    except Exception: return None

def build_fn_bounds():
    bounds = set(); i, n = 0, len(MEM) - 5
    while i < n:
        if MEM[i] == 0xE8:
            rel = struct.unpack('<i', MEM[i+1:i+5])[0]
            t = (BASE + i + 5 + rel) & 0xffffffff
            if BASE <= t < BASE + len(MEM): bounds.add(t)
        i += 1
    return sorted(bounds)
FN = build_fn_bounds()
def fn_start(va):
    s = None
    for f in FN:
        if f <= va: s = f
        else: break
    return s

# ---- 1) 消费者：扫描 byte[reg+0x2d] 与 word[reg+0x2c] 的 test/or/and 中带 0x10/0x60 (byte) 或 0x1000/0x6000 (word) ----
print("==== 消费者 (byte@+0x2d / word@+0x2c) 中 F4/F2B 相关比较 ====")
cons = []
i, n = 0, len(MEM) - 10
while i < n:
    ins_list = dis(BASE + i, 10)
    for ins in ins_list:
        if ins.address != BASE + i: break
        if ins.mnemonic in ('test','or','and','cmp') and len(ins.operands) == 2:
            op0, op1 = ins.operands
            if op1.type == CS_OP_IMM:
                m = op1.imm & 0xffffffff
                # byte 形式: disp==0x2d
                if op0.type == CS_OP_MEM and op0.mem.index == 0 and (op0.mem.disp & 0xffffffff)==0x2d and (op0.mem.segment==0):
                    bm = m & 0xff
                    if bm & (0x10 | 0x60):
                        cons.append((ins.address, 'BYTE', ins.mnemonic, bm))
                # word 形式: disp==0x2c
                elif op0.type == CS_OP_MEM and op0.mem.index == 0 and (op0.mem.disp & 0xffffffff)==0x2c:
                    if m & (0x1000 | 0x6000):
                        cons.append((ins.address, 'WORD', ins.mnemonic, m & 0xffff))
    i += 1

from collections import Counter
cc = Counter((k,m) for _,k,_,m in cons)
print("消费者按 (形式,mask) 分布:", dict(cc))
print("总消费者 hits=%d" % len(cons))
# 列出去重
seen=set()
for va, kind, mn, m in cons:
    key=(va,kind,m)
    if key in seen: continue
    seen.add(key)
    tag = 'F4' if (kind=='BYTE' and m==0x10) or (kind=='WORD' and m==0x1000) else ('F2B' if (kind=='BYTE' and m==0x60) or (kind=='WORD' and m==0x6000) else 'MIX')
    print("  [%s] 0x%x %s %s 0x%x" % (tag, va, kind, mn, m))

# ---- 2) setter 调用点 + 参数追踪 ----
SETTERS = {0x49a828: 'F4', 0x49a840: 'F2B'}
for sa, name in SETTERS.items():
    calls=[]
    i, n = 0, len(MEM) - 5
    while i < n:
        if MEM[i] == 0xE8:
            rel = struct.unpack('<i', MEM[i+1:i+5])[0]
            t = (BASE + i + 5 + rel) & 0xffffffff
            if t == sa:
                calls.append(BASE + i)
        i += 1
    print("\n==== %s setter 0x%x : %d callers ====" % (name, sa, len(calls)))
    from collections import Counter as C2
    argcount = C2()
    for ca in calls:
        # 反汇编调用前 48B 窗口
        pre = dis(ca-48, 48)
        arg = '?'
        # 找 push 指令（imm 或 reg），取最接近 call 的那个
        last_push = None
        for ins in pre:
            if ins.address >= ca: break
            if ins.mnemonic == 'push':
                last_push = ins.op_str
        if last_push is not None:
            if last_push.startswith('0x') or last_push.isdigit():
                arg = int(last_push, 16) if last_push.startswith('0x') else int(last_push)
            else:
                # 寄存器 push — 尝试回溯寄存器赋值
                reg = last_push.split()[0] if ' ' in last_push else last_push
                # 在 pre 中找该寄存器最后被 set 的指令
                val = None
                for ins in pre:
                    if ins.address >= ca: break
                    if ins.mnemonic in ('mov','xor','or','and') and len(ins.operands)>=2:
                        if reg_name(ins.operands[0]) == reg:
                            op1 = ins.operands[1]
                            if op1.type == CS_OP_IMM:
                                val = op1.imm & 0xff
                            elif op1.type == CS_OP_REG:
                                val = 'reg:'+reg_name(op1)
                            elif op1.type == CS_OP_MEM:
                                val = 'mem'
                arg = val if val is not None else ('reg:'+reg)
        argcount[arg]+=1
        if len(calls) <= 40:
            print("  0x%x (fn 0x%x) arg=%s" % (ca, fn_start(ca), arg))
    print("  arg 分布:", dict(argcount))
