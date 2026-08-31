# -*- coding: utf-8 -*-
"""续163 探索③：对 44 个 call 0x4802e0 站点，提取调用前两 push（右到左 = base 然后 size），
分类 base 是常量 VA 还是寄存器派生，确认「记录是否参数化资源选择」。"""
import os
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

BASE = 0x400000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(ROOT, 'scripts', '_unpacked_mem.bin'), 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

TARGET = 0x4802E0


def find_call_sites(target):
    sites = []
    i = 0
    n = len(MEM)
    while i < n - 5:
        if MEM[i] == 0xe8:
            rel = int.from_bytes(MEM[i + 1:i + 5], 'little', signed=True)
            if (BASE + i) + 5 + rel == target:
                sites.append(BASE + i)
        i += 1
    return sites


def dis(va, n):
    return list(md.disasm(MEM[va - BASE: va - BASE + n], va))


def main():
    sites = find_call_sites(TARGET)
    const_bases = []
    reg_bases = []
    for s in sites:
        ins = dis(s - 0x30, 0x30)
        # 找 call 前的最后两个 push
        pushes = [x for x in ins if x.mnemonic == 'push']
        # pushes 按地址升序；最后两个即 base(size 倒数第二 / ... ) 注意右到左
        if len(pushes) >= 2:
            p_base = pushes[-2]   # 靠近 call 的第二个 push = base（先 push）
            p_size = pushes[-1]   # 最后一个 push = size
        elif len(pushes) == 1:
            p_base, p_size = pushes[0], None
        else:
            p_base = p_size = None
        base_s = p_base.op_str if p_base else '?'
        size_s = p_size.op_str if p_size else '?'
        # 判定 base 是否常量 VA
        is_const = base_s.lower().startswith('0x')
        tag = 'CONST' if is_const else 'REG '
        line = f'0x{s:06x}  base={base_s:12s} size={size_s:8s} [{tag}]'
        print(line)
        (const_bases if is_const else reg_bases).append((s, base_s, size_s))
    print(f'\n=== 统计：共 {len(sites)} 站；常量基址 {len(const_bases)}，寄存器派生基址 {len(reg_bases)} ===')
    if reg_bases:
        print('--- 寄存器派生基址站点（须溯源）---')
        for s, b, sz in reg_bases:
            print(f'  0x{s:06x}  base={b}  size={sz}')


if __name__ == '__main__':
    main()
