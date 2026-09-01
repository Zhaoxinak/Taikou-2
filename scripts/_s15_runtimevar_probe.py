#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S15 段C 16 处 runtime-var set_c 写者：回向 def-use 追踪 val 语义源（续217 准备）。
set_c(0x49c500) = thiscall(ecx=0x5203c0)， byte[0x5203c0+0x13+idx]=val，idx&0xff。
对每个 runtime-var 调用点，从 set_c_call 回向到 owner_fn，找 val 寄存器最后定义源。
"""
import os, json
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from _disasm_all import load_image, disasm_all

BASE = 0x400000
MEM = load_image()
MD = Cs(CS_ARCH_X86, CS_MODE_32)
MD.detail = False

def span(lo, hi):
    res = []
    for ins in disasm_all(MD, MEM, BASE):
        if ins.address >= lo and ins.address < hi:
            res.append(ins)
        if ins.address >= hi:
            break
    return res

def fmt(ins):
    return f"{ins.address:#08x}  {ins.mnemonic} {ins.op_str}"

# 寄存器写入目标提取（简单：op_str 形如 "eax, ..." 或 "byte ptr [ecx+5]"）
def writes_to(ins, reg):
    os_ = ins.op_str
    if ins.mnemonic.startswith('mov') or ins.mnemonic in ('add','sub','xor','and','or','shl','shr','lea'):
        # 目标是第一个操作数
        dst = os_.split(',')[0].strip()
        return reg == dst
    if ins.mnemonic.startswith('call'):
        # cdecl 调用通常改写 eax/edx/ecx
        return reg in ('eax','edx','ecx')
    return False

def trace_val_source(owner_fn, call_va, val_reg):
    insns = span(owner_fn, call_va+4)
    # 从 call 往前找最后一条写 val_reg 的指令
    last_def = None
    calls_seen = []
    for ins in reversed(insns):
        if ins.address == call_va:
            continue
        if ins.mnemonic.startswith('call'):
            calls_seen.append(ins.address)
        if writes_to(ins, val_reg):
            last_def = ins
            break
    return last_def, calls_seen

def main():
    _here = os.path.dirname(os.path.abspath(__file__))
    d = json.load(open(os.path.join(_here, 's15_segc_fullmap.json')))
    rt = [e for e in d['mapping'] if e['val_kind']=='runtime-var']
    print(f"===== {len(rt)} 个 runtime-var 写者：val 语义源回向追踪 =====")
    for e in rt:
        cva = int(e['set_c_call'], 16)
        ofn = int(e['owner_fn'], 16)
        vr = e['val']
        last_def, calls = trace_val_source(ofn, cva, vr)
        print(f"\n-- set_c_call={e['set_c_call']} owner={e['owner_fn']} segC_idx={e['segC_idx']} val_reg={vr} event_bits={e['event_bits']}")
        print(f"     val 最后定义: {fmt(last_def) if last_def else 'NONE(within owner)'}")
        if calls:
            print(f"     回向调用点(最近): " + ", ".join(f"{c:#08x}" for c in calls[:4]))
        # 也打印调用点前 6 条上下文
        ctx = span(max(ofn, cva-0x30), cva+4)[-8:]
        for ins in ctx:
            mark = " <<CALL" if ins.address==cva else ""
            print("     ctx:", fmt(ins), mark)

if __name__ == '__main__':
    main()
