# -*- coding: utf-8 -*-
"""P0-(A) 全镜像函数指针表扫描：找「按记录类型索引的 handler 表」。

思路：SNDATA 记录类型 = id_word & 0xff（最多 256 型），若存在 type->handler 分发表，
则必然是一段**连续 dword**，每一项都指向代码段内的有效函数入口。
扫描连续有效代码指针的最长游程即可定位。

用法：
    python scripts/_sndata_fptr_table_scan.py              # 默认 0x400000-0x530000, minlen=24
    python scripts/_sndata_fptr_table_scan.py --minlen 100
    python scripts/_sndata_fptr_table_scan.py --lo 0x500000 --hi 0x530000
"""
import argparse
import os
import struct

BASE = 0x400000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(ROOT, 'scripts', '_unpacked_mem.bin'), 'rb').read()
IMAGE_END = BASE + len(MEM)

# 代码段范围（脱壳映像 text：OEP 0x4f44b0，末尾 ~0x4f0000 之后是数据/资源）
CODE_LO = 0x401000
CODE_HI = 0x4f0000

# 数据段内「不可能是指针」的哨兵
JUNK = {0x00000000, 0xFFFFFFFF}


def is_code_ptr(v):
    return CODE_LO <= v < CODE_HI


def scan(lo, hi, minlen):
    """扫 lo..hi 内连续 dword 全为有效代码指针的最长游程。"""
    runs = []
    start_addr = None
    cur = []
    for off in range(lo - BASE, hi - BASE - 3, 4):
        va = BASE + off
        (v,) = struct.unpack_from('<I', MEM, off)
        if v not in JUNK and is_code_ptr(v):
            if not cur:
                start_addr = va
            cur.append(v)
        else:
            if len(cur) >= minlen:
                runs.append((start_addr, list(cur)))
            cur = []
            start_addr = None
    if len(cur) >= minlen:
        runs.append((start_addr, list(cur)))
    runs.sort(key=lambda r: -len(r[1]))
    return runs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lo', default='0x400000')
    ap.add_argument('--hi', default='0x530000')
    ap.add_argument('--minlen', type=int, default=24)
    ap.add_argument('--top', type=int, default=25)
    a = ap.parse_args()

    lo = int(a.lo, 16)
    hi = min(int(a.hi, 16), IMAGE_END)
    print(f'=== 函数指针表扫描 [{lo:#x}, {hi:#x})  minlen={a.minlen} ===')
    print(f'    代码段判定: [{CODE_LO:#x}, {CODE_HI:#x})')
    runs = scan(lo, hi, a.minlen)
    print(f'    命中 {len(runs)} 张候选表（>= {a.minlen} 项连续代码指针）\n')

    for addr, ents in runs[:a.top]:
        n = len(ents)
        uniq = len(set(ents))
        inc = sum(1 for i in range(n - 1) if ents[i + 1] > ents[i])
        mono_ratio = inc / max(1, n - 1)
        lo_e, hi_e = min(ents), max(ents)
        print(f'  @{addr:#08x}  n={n:<5d} uniq={uniq:<5d} 递增率={mono_ratio:.2f} '
              f'范围[{lo_e:#08x}..{hi_e:#08x}]')
        print(f'      前8: ' + ' '.join(f'{v:#x}' for v in ents[:8]))
        print(f'      后4: ' + ' '.join(f'{v:#x}' for v in ents[-4:]))

    # 单独列出「>=128 项」的超大表（256 型分发表的强候选）
    big = [r for r in runs if len(r[1]) >= 128]
    if big:
        print(f'\n=== 超大表（>=128 项，256 型分发表强候选）共 {len(big)} 张 ===')
        for addr, ents in big:
            print(f'  @{addr:#08x}  n={len(ents)}  uniq={len(set(ents))}')


if __name__ == '__main__':
    main()
