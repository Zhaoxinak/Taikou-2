#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续171：对 word[+0x2c] bit15/bit7 的 SET/CLR 站点，分析调用方 + 站点上下文。
目标函数：实际写 bit15 / bit7 的函数。输出：每个函数的调用方、站点附近反汇编、内部调用。"""
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

import os, re, bisect
from collections import defaultdict
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()

def dis(va, n):
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.skipdata = True
    off = va - BASE
    return list(md.disasm(bytes(MEM[off:off+n]), va))

INS = dis(BASE, len(MEM))
all_funcs = set([0x4f44b0, 0x400000])
for i in INS:
    if i.mnemonic == "call" and i.op_str.startswith("0x"):
        try: all_funcs.add(int(i.op_str, 16))
        except: pass
all_funcs = sorted(all_funcs)
def func_of(va): return all_funcs[max(0, bisect.bisect_right(all_funcs, va) - 1)]
func_insns = defaultdict(list)
for i in INS: func_insns[func_of(i.address)].append(i)

# 找调用方
callers = defaultdict(set)
for fn, ilist in func_insns.items():
    for j in ilist:
        if j.mnemonic == "call" and j.op_str.startswith("0x"):
            try: callers[int(j.op_str,16)].add(fn)
            except: pass

ANCHOR = {
    0x49a7d0:"set_lord_idx",0x49a880:"inc_loyalty",0x49ffc0:"affinity_score",
    0x49c460:"S15_set_a",0x49c4b0:"S15_set_b",0x49a990:"castle_rec_copy",
    0x47b900:"display_msg",0x4ebd60:"RNG",0x45e3e0:"build_cand_pool",
    0x49f5e0:"get_player",0x49f830:"get_slot",0x470690:"is_alive",
    0x47fc60:"sndata_fanout",0x49b960:"shared_setter_lib",0x441cc0:"武将選択",
    0x49a750:"copy_prov",0x4a35e0:"s6_add",0x49a7e0:"set_status_b8_10",
    0x49f6b0:"get_ctx",0x4ebcd0:"sat_sub",0x4ebca0:"sat_add",
    0x4a5571:"継承転封",0x4a3920:"全員浪人化A",0x46a4a0:"主君再割当",
    0x452b21:"登用",0x4a5033:"出奔",0x4a580e:"転属",0x4a3eab:"役職解除",
    0x4c3322:"功勲结算",0x4cb9e0:"相性離反",0x440e19:"玩家改易",
    0x40ff2c:"浪人生成A",0x41004b:"浪人生成B",0x4dd7c0:"S5",
    0x49ba30:"S6b2_4",0x49bd50:"set_status",0x49bd70:"set_status",0x49bd90:"set_status",
    0x4a3260:"inc_loyalty2",0x4cf240:"全局复位",0x4cf280:"单记录复位",
}

TARGETS = [0x439190, 0x457a10, 0x48fb00, 0x43dd20, 0x46b2f0]

for t in TARGETS:
    print("="*78)
    print("函数 0x%06x  调用方数=%d" % (t, len(callers[t])))
    cl = sorted(callers[t])
    print("  调用方:", " ".join("0x%06x" % c for c in cl[:40]))
    # 站点附近反汇编
    ilist = func_insns.get(t, [])
    # 找 SET/CLR 站点地址
    sites = []
    for ins in ilist:
        m, op = ins.mnemonic, ins.op_str
        rm = re.match(r'(ah|al|ax|eax),\s*(0x[0-9a-f]+|\d+)$', op)
        if rm and m in ("or","and"):
            imm = int(rm.group(2),16) if rm.group(2).startswith('0x') else int(rm.group(2),10)
            if imm in (0x8000,0x7fff,0x80,0x7f):
                sites.append(ins.address)
    if not sites:
        # 内存形式
        for ins in ilist:
            mm = re.match(r'(?:word|byte) ptr \[([^\]]+)\],\s*(0x[0-9a-f]+|\d+)$', ins.op_str)
            if mm and m in ("or","and"):
                d = mm.group(1); imm=int(mm.group(2),16) if mm.group(2).startswith('0x') else int(mm.group(2),10)
                if ("0x2c" in d or "0x2d" in d) and imm in (0x8000,0x7fff,0x80,0x7f):
                    sites.append(ins.address)
    for s in sites:
        idx = [i.address for i in ilist].index(s)
        lo = max(0, idx-6); hi = min(len(ilist), idx+7)
        print("  --- 站点 0x%x 附近 ---" % s)
        for ins in ilist[lo:hi]:
            mark = " >>>" if ins.address==s else "    "
            print("  0x%x%s %-8s %s" % (ins.address, mark, ins.mnemonic, ins.op_str))
    # 内部调用（锚点解析）
    anc = set()
    for j in ilist:
        if j.mnemonic=="call" and j.op_str.startswith("0x"):
            try:
                v=int(j.op_str,16)
                if v in ANCHOR: anc.add(ANCHOR[v])
            except: pass
    print("  内部锚点:", " ".join(sorted(anc)))
    print()
