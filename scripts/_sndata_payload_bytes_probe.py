# -*- coding: utf-8 -*-
"""续164 探索：枚举记录缓冲 0x522c88/0x522c60/0x522c70/0x522c98/0x522ca0/0x522cc0 在
分发门控 + 簇 handler 中的全部读指令，提取 [base+disp] 位移 → 对应 payload 字节偏移，
看哪些 payload 字节参与路由/初始化。"""
import os
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

BASE = 0x400000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(ROOT, 'scripts', '_unpacked_mem.bin'), 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

RECB = ['0x522c88', '0x522c60', '0x522c70', '0x522c98', '0x522ca0', '0x522cc0']

# 分发门控 + 簇 handler 候选
FUNCS = {
    'matcher 0x47b390': 0x47b390,
    'matcher_impl 0x47b2e0': 0x47b2e0,
    'predicate 0x47fb80': 0x47fb80,
    'record_parser 0x47f350': 0x47f350,
    'type0 h0 0x492e20': 0x492e20,
    'type0 h1 0x493140': 0x493140,
    'type0 h2 0x492f80': 0x492f80,
    'type1 h0 0x492ed0': 0x492ed0,
    'type1 h1 0x4931f0': 0x4931f0,
    'clu_else 0x524740': 0x524740,
}


def dis(va, n):
    return list(md.disasm(MEM[va - BASE: va - BASE + n], va))


def main():
    for name, va in FUNCS.items():
        print(f'\n===== {name} @0x{va:06x} =====')
        ins = dis(va, 0x400)
        hits = 0
        for x in ins:
            s = f'{x.mnemonic} {x.op_str}'
            for rb in RECB:
                if rb in s:
                    print(f'  0x{x.address:06x}  {s}')
                    hits += 1
                    break
        if hits == 0:
            print('  (无记录缓冲读取)')


if __name__ == '__main__':
    main()
