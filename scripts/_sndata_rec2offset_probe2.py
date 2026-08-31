# -*- coding: utf-8 -*-
"""续163 探索②：全镜像扫 `call 0x4802e0` 调用点，dump 每个调用点前的 push 参数，
确认「资源表基址 + selector 尺寸」是硬编码常量还是记录派生。"""
import os
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

BASE = 0x400000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(ROOT, 'scripts', '_unpacked_mem.bin'), 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def find_call_sites(target):
    """target = 被调 VA。返回所有 call 站点 VA 列表。"""
    sites = []
    # e8 rel32：指令 = e8 + 4 字节小端；目标 = next_va + rel32
    i = 0
    n = len(MEM)
    while i < n - 5:
        if MEM[i] == 0xe8:
            rel = int.from_bytes(MEM[i + 1:i + 5], 'little', signed=True)
            callee = (BASE + i) + 5 + rel
            if callee == target:
                sites.append(BASE + i)
        i += 1
    return sites


def dis(va, n):
    return list(md.disasm(MEM[va - BASE: va - BASE + n], va))


def main():
    target = 0x4802E0
    sites = find_call_sites(target)
    print(f'=== `call 0x4802e0` 共 {len(sites)} 个调用点 ===')
    for s in sites:
        # dump 0x40 字节（含 call 前后）
        print(f'\n--- call @0x{s:06x}（所在函数入口推断）---')
        ins = dis(s - 0x30, 0x50)
        for x in ins:
            marker = ' <<<CALL' if x.address == s else ''
            print(f'  0x{x.address:06x}  {x.mnemonic} {x.op_str}{marker}')


if __name__ == '__main__':
    main()
