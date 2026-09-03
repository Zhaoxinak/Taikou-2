# -*- coding: utf-8 -*-
"""续241 勘察 #1：13 个写器调用点的函数归属 + 逐站语义追踪（临时探针）"""
import os, json, bisect
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, x86_const as X

BASE = 0x400000
HERE = os.path.dirname(os.path.abspath(__file__))
MEM = open(os.path.join(HERE, '_unpacked_mem.bin'), 'rb').read()
MD = Cs(CS_ARCH_X86, CS_MODE_32); MD.skipdata = True; MD.detail = True

def raw(va, n): return MEM[va - BASE: va - BASE + n]
def dis(va, n): return list(MD.disasm(raw(va, n), va))

SITES = {
    'k1马术': [0x45d9e3, 0x45da41],
    'k2算术': [0x458f8e, 0x458fc0],
    'k3剑术': [0x448b56],
    'k4忍术': [0x451f98],
    'k6洋枪': [0x44736c, 0x4473dd],
    'k8礼法': [0x45aefd, 0x45af25],
    'k9茶道': [0x442e5d, 0x442ed1, 0x44304c],
}
ALLS = sorted(a for lst in SITES.values() for a in lst)

def build_func_index():
    """从 msgx catalog func 字段 + 已知锚收集函数起点；返回 sorted 列表"""
    d = json.load(open(os.path.join(HERE, 'msgx_id_map.json'), encoding='utf-8'))
    fs = set()
    for s in d['sites']:
        try: fs.add(int(s['func'], 16))
        except ValueError: pass
    fs |= {0x442d70, 0x442f70, 0x451e70, 0x451f90, 0x45d950, 0x458e20,
           0x448990, 0x447230, 0x45ade0, 0x45af50, 0x442a80, 0x442bd0}
    return sorted(fs)

FI = build_func_index()

def enclosing(va):
    i = bisect.bisect_right(FI, va) - 1
    assert i >= 0, hex(va)
    nxt = FI[i + 1] if i + 1 < len(FI) else FI[i] + 0x400
    return FI[i], nxt

def fmt_ins(x):
    ops = x.op_str
    if x.mnemonic == 'call' and len(x.operands) == 1 and x.operands[0].type == X.X86_OP_IMM:
        t = x.operands[0].imm
        # 标注写器族
        if 0x4a3040 <= t < 0x4a3040 + 0x200:
            k = (t - 0x4a3040) // 0x20
            ops += '  <== HELPER k%d' % k
        ops += '  ; ->0x%x' % t
    return '0x%06x  %-14s %s' % (x.address, x.mnemonic, ops)

def show_window(va, pre=14, post=6):
    f, fend = enclosing(va)
    print('  [func 0x%06x .. 0x%06x] window @ 0x%06x' % (f, fend, va))
    body = list(MD.disasm(raw(f, fend - f), f))
    idx = next((i for i, x in enumerate(body) if x.address == va), None)
    if idx is None:
        print('  !! call site NOT aligned within func range disasm; fallback raw from func')
        return
    for x in body[max(0, idx - pre): idx + post]:
        mark = ' >>>' if x.address == va else ''
        print('   ' + fmt_ins(x) + mark)

for name, lst in SITES.items():
    for a in lst:
        print('=' * 100)
        print('%s site 0x%06x  enclosing func 0x%06x' % (name, a, enclosing(a)[0]))
        show_window(a)
