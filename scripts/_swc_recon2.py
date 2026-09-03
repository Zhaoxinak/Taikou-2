# -*- coding: utf-8 -*-
"""续241 勘察 #2：宿主函数全量反汇编落盘（临时探针）"""
import os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, x86_const as X

BASE = 0x400000
HERE = os.path.dirname(os.path.abspath(__file__))
MEM = open(os.path.join(HERE, '_unpacked_mem.bin'), 'rb').read()
MD = Cs(CS_ARCH_X86, CS_MODE_32); MD.skipdata = True; MD.detail = True

FUNCS = {
    'f1_mayadoko_45d950': (0x45d950, 0x45dc50, 'k1 马屋仕事'),
    'f2_shounin_458e20': (0x458e20, 0x459000, 'k2 商家学算术'),
    'f3_dojo_448990': (0x448990, 0x448d20, 'k3 道场'),
    'f4_nin_451f90': (0x451f90, 0x452000, 'k4 忍术 leaf'),
    'f6_teppo_447230': (0x447230, 0x447910, 'k6 铁炮锻冶'),
    'f8_tera_45ade0': (0x45ade0, 0x45af50, 'k8 寺庙礼法'),
    'f9a_cha_442d70': (0x442d70, 0x442f70, 'k9a/b 茶人品茶'),
    'f9b_cha2_442f70': (0x442f70, 0x443350, 'k9c 茶人品茶2'),
}

def fmt_ins(x):
    ops = x.op_str
    if x.mnemonic == 'call' and len(x.operands) == 1 and x.operands[0].type == X.X86_OP_IMM:
        t = x.operands[0].imm
        if 0x4a3040 <= t < 0x4a3040 + 0x200:
            k = (t - 0x4a3040) // 0x20
            ops += '  <== K%d' % k
        ops += '  ;->0x%x' % t
    return '0x%06x  %-16s %s' % (x.address, x.mnemonic + (' ' + x.op_str if x.op_str else ''), '')

def dump(name, f, n, tag):
    body = list(MD.disasm(MEM[f - BASE: n - BASE], f))
    out = ['# %s  %s  0x%x..0x%x' % (name, tag, f, n)]
    for x in body:
        line = '0x%06x  %-7s %s' % (x.address, x.mnemonic, x.op_str)
        if x.mnemonic == 'call':
            line += '   ;;'
            if len(x.operands) == 1 and x.operands[0].type == X.X86_OP_IMM:
                t = x.operands[0].imm
                if 0x4a3040 <= t < 0x4a30c0:
                    line += ' <== K%d skill-writer' % ((t - 0x4a3040) // 0x20)
                elif t in (0x4a30c0,):
                    line += ' <== K4'
                elif 0x4a30e0 <= t < 0x4a3180:
                    line += ' <== K%d skill-writer' % ((t - 0x4a3040) // 0x20)
                elif t in (0x4a31b0, 0x4a3180, 0x4a3210):
                    line += ' <== field-adj helper'
                elif t == 0x4ebd60:
                    line += ' <== RNG'
                elif t == 0x4ebca0:
                    line += ' <== sat_add'
                elif t == 0x4ebcd0:
                    line += ' <== sat_sub'
                elif t == 0x49f5e0:
                    line += ' <== get_player_entity'
                elif t == 0x49f610:
                    line += ' <== get_other_entity'
        out.append(line)
    open(os.path.join(HERE, '_swc_dump_' + name + '.txt'), 'w', encoding='utf-8').write('\n'.join(out))
    print('%s: %d ins' % (name, len(body)))

for name, (f, n, tag) in FUNCS.items():
    dump(name, f, n, tag)
