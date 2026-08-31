# -*- coding: utf-8 -*-
"""P0-(A) 找所有「读记录 payload 缓冲」的函数，判定分派是 per-type 代码还是数据驱动。

判据：
  - 若读 0x522cXX 的函数有 ~164 个  => 存在 per-type handler（再找分发表）
  - 若只有个位数                    => 数据驱动解释（改追 schema 表）

用法：python scripts/_sndata_buf_readers.py
"""
import bisect
import os
import struct
from collections import defaultdict

from capstone import CS_ARCH_X86, CS_MODE_32, Cs

BASE = 0x400000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(ROOT, 'scripts', '_unpacked_mem.bin'), 'rb').read()

CODE_LO, CODE_HI = 0x401000, 0x4f0000
# 0x522c60 / 0x522c70 各 1B，0x522c88 起 43B payload；留余量
BUF_LO, BUF_HI = 0x522C50, 0x522D00


def build_call_targets():
    """所有 call rel32 (e8) 目标 = 函数入口集合（本项目既定函数边界法）。"""
    tgts = set()
    for off in range(CODE_LO - BASE, CODE_HI - BASE - 5):
        if MEM[off] == 0xE8:
            (rel,) = struct.unpack_from('<i', MEM, off + 1)
            t = BASE + off + 5 + rel
            if CODE_LO <= t < CODE_HI:
                tgts.add(t)
    return sorted(tgts)


def find_hits():
    """扫描代码段内所有落在 [BUF_LO, BUF_HI) 的 dword（作为 disp32 或 imm32）。"""
    hits = []
    for off in range(CODE_LO - BASE, CODE_HI - BASE - 4):
        (v,) = struct.unpack_from('<I', MEM, off)
        if BUF_LO <= v < BUF_HI:
            hits.append((BASE + off, v))
    return hits


def decode_insn_containing(addr, val):
    """尝试从 addr 往前最多 8 字节反汇编，找一条覆盖 addr 且引用 val 的指令。"""
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    for back in range(0, 9):
        s = addr - back
        if s < CODE_LO:
            break
        try:
            ins = next(md.disasm(mem_slice(s, 16), s))
        except StopIteration:
            continue
        if ins.address <= addr < ins.address + ins.size and f'{val:#x}' in ins.op_str:
            return ins
    return None


def mem_slice(va, n):
    return MEM[va - BASE: va - BASE + n]


def main():
    print('=== 构建函数入口集合 (call rel32 目标) ===')
    tgts = build_call_targets()
    print(f'    {len(tgts)} 个函数入口\n')

    print(f'=== 扫描代码段内 [{BUF_LO:#x}, {BUF_HI:#x}) 的字面引用 ===')
    hits = find_hits()
    print(f'    字面命中 {len(hits)} 处\n')

    fn_map = defaultdict(lambda: defaultdict(set))
    decoded = skipped = 0
    for addr, val in hits:
        ins = decode_insn_containing(addr, val)
        if ins is None:
            skipped += 1
            continue
        decoded += 1
        i = bisect.bisect_right(tgts, ins.address) - 1
        fn = tgts[i] if i >= 0 else ins.address
        fn_map[fn][val].add((ins.address, ins.mnemonic, ins.op_str))

    print(f'    可解码 {decoded} 处，无法归属指令 {skipped} 处')
    print(f'    => 涉及函数 {len(fn_map)} 个\n')

    print('=== 按「引用次数」排序的函数（=记录缓冲消费者）===')
    ranked = sorted(fn_map.items(),
                    key=lambda kv: -sum(len(v) for v in kv[1].values()))
    for fn, offs in ranked[:30]:
        total = sum(len(v) for v in offs.values())
        ks = sorted(offs.keys())
        print(f'  {fn:#08x}  引用 {total:3d} 次  触及偏移 {[hex(k) for k in ks][:8]}')
        # 打印前 3 条
        shown = 0
        for k in ks:
            for (a, mn, ops) in sorted(offs[k])[:2]:
                print(f'        {a:#08x}  {mn:<8s} {ops}')
                shown += 1
                if shown >= 3:
                    break
            if shown >= 3:
                break
        print()

    print('=== 结论判据 ===')
    print(f'    读记录缓冲的函数数 = {len(fn_map)}')
    print('    ~164 => per-type handler 存在（继续找分发表）')
    print('    <=10 => 数据驱动解释（改追 schema 表，非函数分派）')


if __name__ == '__main__':
    main()
