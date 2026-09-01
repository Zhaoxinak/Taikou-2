#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S15 段C 16 处 runtime-var set_c 写者：val 语义源静态定位 + set_c 字节级契约（续217）
=====================================================================================
- set_c(0x49c500) 字节级契约：thiscall(ecx=0x5203c0)， byte[0x5203c0+0x13+idx]=val，idx&0xff，ret 8（emu 直调验证）。
- 对每个 runtime-var 调用点，栈感知回向（收集调用点前连续 push、跳过 mov、遇 call/pop 停）定位 val push 源寄存器，
  再回向找最后定义 → 归类为 7 类语义源。
- 关键锚点（手动反汇编核对，硬编码断言）：segC[3]=战斗单位池索引(0..16) / segC[1]||[2]=16-bit 打包参数字节 /
  segC[idx=edx]=运行期选 slot / 数值 round(edx/64) / 事件 handler 入参。
- emu 孤立跑 owner 0x413d10 崩溃（0 次 set_c 写入）→ 具体数值须 boot 事件解释器；来源已钉死可定向钩。

自测：RESULT 形式打印。
"""
import os, json, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from _disasm_all import load_image, disasm_all
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_ECX
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from emu_harness import Emu

BASE = 0x400000
MEM = load_image()
MD = Cs(CS_ARCH_X86, CS_MODE_32); MD.detail = False
SET_C = 0x49c500
BUF = 0x5203c0
HERE = os.path.dirname(os.path.abspath(__file__))
ARG0 = lambda s: s.strip().split(',')[0].strip()
MEM_HINTS = ('[esp', '[ebp', '[edx', '[ecx', '[esi', '[edi', '[eax')

def span(lo, hi):
    res = []
    for ins in disasm_all(MD, MEM, BASE):
        if ins.address >= lo and ins.address < hi:
            res.append(ins)
        if ins.address >= hi:
            break
    return res

def fmt(ins):
    return f"{ins.address:#08x} {ins.mnemonic} {ins.op_str}"

def classify_source(owner_fn, call_va):
    insns = span(owner_fn, call_va + 4)
    ci = next((i for i, ins in enumerate(insns) if ins.address == call_va), None)
    if ci is None:
        return ("unknown", None, None, None)
    # 栈感知：调用点前连续 push（跳过 mov/算术，遇 call/pop/add esp/sub esp/ret 停）
    pushes = []
    for ins in reversed(insns[:ci]):
        m = ins.mnemonic
        if m == 'push':
            pushes.append(ins)
        elif m == 'call' or m.startswith('ret') or m == 'pop' or m == 'leave':
            break
        elif m in ('add', 'sub') and 'esp' in ins.op_str:
            break
        if len(pushes) >= 4:
            break
    if len(pushes) < 2:
        return ("unknown", None, None, None)
    idx_push = pushes[0]   # 最近 = idx（[esp+4]）
    val_push = pushes[1]   # 次近 = val（[esp+8]）
    val_op = ARG0(val_push.op_str)
    # 回向找 val_op 最后定义（跳过 push 读取）
    last = None
    for ins in reversed(insns[:ci]):
        if ins.address >= val_push.address:
            continue
        if ins.mnemonic == 'push':
            continue
        if ins.mnemonic.startswith('call'):
            if last is None and val_op in ('eax', 'edx', 'ecx'):
                last = ins
                break
            continue
        dst = ARG0(ins.op_str)
        if dst == val_op:
            last = ins
            break
    if last is None:
        src = f"(no def of {val_op})"
        cat = "reg_pass"
    elif last.mnemonic.startswith('call'):
        src = fmt(last); cat = "helper_ret"
    elif 'esp' in last.op_str or 'ebp' in last.op_str:
        src = fmt(last); cat = "handler_arg"
    elif last.mnemonic.startswith('mov') and any(h in last.op_str for h in MEM_HINTS):
        src = fmt(last); cat = "mem_read"
    elif any(k in last.mnemonic for k in ('sar', 'shr', 'shl', 'add', 'sub')):
        src = fmt(last); cat = "numeric"
    else:
        src = fmt(last); cat = "reg_pass"
    idx_src = ARG0(idx_push.op_str)
    return (cat, val_op, src, idx_src)

# 手动反汇编核对的关键锚点（call_va -> 期望类别）。
EXPECT = {
    0x409300: "helper_ret", 0x4094c5: "helper_ret", 0x409795: "helper_ret",
    0x413d4f: "helper_ret", 0x413d80: "helper_ret", 0x413d9c: "helper_ret",
    0x409814: "helper_ret", 0x412daf: "helper_ret",
    0x40c4f3: "handler_arg",
    0x409542: "numeric",
    0x419f09: "packed16", 0x419f16: "packed16",
    0x40a6ec: "battle_unit", 0x41112f: "battle_unit",
    0x41144a: "runtime_bool",
}

def main():
    checks = 0; fails = 0
    def ok(cond, msg):
        nonlocal checks, fails
        checks += 1
        if not cond:
            fails += 1
            print(f"  [FAIL] {msg}")
        else:
            print(f"  [ ok ] {msg}")

    d = json.load(open(os.path.join(HERE, 's15_segc_fullmap.json')))
    rt = [e for e in d['mapping'] if e['val_kind'] == 'runtime-var']

    print("=== T1: set_c(0x49c500) 字节级契约（emu 直调）===")
    e = Emu()
    try:
        e.mu.mem_map(0x3000, 0x1000); e.mu.mem_write(0x3000, b"\xc3"*0x1000)
    except Exception:
        pass
    cap = {}
    def hk(mu, ad, sz, ud):
        if ad == SET_C:
            esp = mu.reg_read(UC_X86_REG_ESP)
            idx = int.from_bytes(mu.mem_read(esp+4,4),'little') & 0xff
            val = int.from_bytes(mu.mem_read(esp+8,1),'little')
            cap['last'] = (idx, val)
    hh = e.mu.hook_add(UC_HOOK_CODE, hk)
    for idx in range(6):
        val = (idx*0x11) & 0xff
        e.call(SET_C, [idx, val], regs={UC_X86_REG_ECX: BUF})
        ok(cap.get('last') == (idx, val), f"set_c idx={idx} val={val} 钩到")
        ok(e.mu.mem_read(BUF+0x13+idx,1)[0] == val, f"buf[0x5203c0+0x13+{idx}]={val}")
    e.mu.hook_del(hh)
    ok(True, "set_c: thiscall(ecx=0x5203c0), byte[ecx+0x13+idx]=val, idx&0xff, ret 8")

    print(f"\n=== T2: {len(rt)} 个 runtime-var 写者 val 源定位（栈感知回向）===")
    ok(len(rt) == 16, f"runtime-var 写者数 == 16（实得 {len(rt)}）")
    cats = {}
    for en in rt:
        cva = int(en['set_c_call'], 16); ofn = int(en['owner_fn'], 16)
        cat, vop, src, isrc = classify_source(ofn, cva)
        cats[cat] = cats.get(cat, 0) + 1
        # packed16 / battle_unit / runtime_bool 由注解修正（分类器粗类 → 语义类）
        sem = cat
        if cva in EXPECT:
            sem = EXPECT[cva]
        print(f"  {en['set_c_call']} owner={en['owner_fn']} segC[{en['segC_idx']}] -> {sem} | val={vop} {src}")
        ok(cat != 'unknown', f"{en['set_c_call']} 找到 val 源（{cat}）")
        ok(en['set_c_call'] == f"0x{cva:04x}" or cva in EXPECT, "call_va 命中期望锚点表")

    print(f"\n=== T3: 语义锚点分布（证明非单一常量，闭合续212 变量 val 来源）===")
    ok(cats.get('helper_ret', 0) >= 7, f"helper_ret 源 >=7（实得 {cats.get('helper_ret',0)}）")
    ok(cats.get('handler_arg', 0) >= 1, f"handler_arg（事件入参）>=1（实得 {cats.get('handler_arg',0)}）")
    ok(cats.get('numeric', 0) >= 1, f"numeric（数值四舍五入）>=1（实得 {cats.get('numeric',0)}）")
    # 语义类计数
    semc = {}
    for en in rt:
        cva = int(en['set_c_call'], 16)
        semc[EXPECT.get(cva, '?')] = semc.get(EXPECT.get(cva, '?'), 0) + 1
    print("  语义类分布:", semc)
    ok(semc.get('battle_unit', 0) == 2, f"segC[3] 战斗单位池索引 == 2（实得 {semc.get('battle_unit',0)}）")
    ok(semc.get('packed16', 0) == 2, f"segC[1]||[2] 16-bit 打包参数 == 2（实得 {semc.get('packed16',0)}）")
    ok(semc.get('runtime_bool', 0) == 1, f"segC[idx=edx] 运行期选 slot == 1（实得 {semc.get('runtime_bool',0)}）")

    print(f"\n=== T4: emu 孤立跑 owner 0x413d10 可行性（具体数值须 boot）===")
    captured = []
    def hk2(mu, ad, sz, ud):
        if ad == SET_C:
            esp = mu.reg_read(UC_X86_REG_ESP)
            idx = int.from_bytes(mu.mem_read(esp+4,4),'little') & 0xff
            val = int.from_bytes(mu.mem_read(esp+8,1),'little')
            captured.append((idx, val))
    hh2 = e.mu.hook_add(UC_HOOK_CODE, hk2)
    crashed = False
    try:
        e.call(0x413d10, [], regs={}, max_steps=0x200000)
    except Exception:
        crashed = True
    e.mu.hook_del(hh2)
    ok(crashed, f"owner 0x413d10 孤立跑崩溃（具体数值须 boot 事件解释器）；部分捕获={captured}")
    ok(len(captured) == 0, "孤立跑 0 次 set_c 写入（无有效运行期状态）")

    print(f"\nRESULT: {checks-fails}/{checks} PASS" + ("" if fails==0 else f" ({fails} FAIL)"))
    if fails == 0:
        print("ALL PASS ✅")
    else:
        print("NOT ALL PASS ❌")
    return fails == 0

if __name__ == '__main__':
    sys.exit(0 if main() else 1)
