# -*- coding: utf-8 -*-
"""太閤立志伝2 —— SNDATA 记录「类别→资源表→payload 选择器」schema 参考实现（续161）

结论（2026-08-31 续161）：承接续160「handler 簇经 0x4802e0/0x492800/0x4ec8c0 读 0x522ca0 写入游戏表」。

🔑 重大重构 P0：833 条 SNDATA 记录**不是「统一 43B payload schema」**，而是
   **剧本资源/资产 + 数据初始化「指令」**。证据：
   ① 各「类别 handler 簇」持有**资源文件名表**（不是字段描述符！）：
        - `0x506b20`（type-0 簇 `0x492e20` 用）= B:MAPCHIP.LZW / B:MAPCHAR.LZW /
          B:SHOP_BG.LZW / B:SHOP_OBJ.LZW / B:SHOP_MSK.LZW / B:ANMSEQ.LZW
        - `0x506ba0`（type-1 簇 `0x492ed0` 用）= C:TOWNCHIP.LZW / C:TOWNCHAR.LZW /
          C:HEXMES.LZW / C:KOSENGRP.LZW / D:FACE.LZW / A:EXTFACE.PK8
   ② 每条记录经类别 handler 加载其类别资源表中的一个资源（selector 选索引）+ 参数。
      ⇒ **type→field schema 是「类别作用域」的：type → 类别 handler → 资源表
        (0x506b20…) → payload 选择器字段 → 具体资源 + 参数**。
   ③ payload 选择器经**定长构造器 `0x4ec8c0`**（selector 字节 &0xfb，mod 4 →
      尺寸 0/1/2/0x1000）经 `[0x4fb07c]` 注册；资源经 `0x492800`→`0x4f40b0` 登记。
   ④ `0x50d820`/`0x50d834` 是 **GBK 消息串**（武器/不能使用…），说明记录还含
      **消息/事件指令**维度，而非「类型匹配模板」。

⚠️ 仍未知：① 每类别 payload 选择器的精确偏移（须追 0x4ec8c0/0x47f350 对 0x522ca0 的字段布局）；
   ② master 注册间接分派器（选类别 handler）无静态 xref；③ 全类别资源表枚举 + 类别↔handler↔表 全表。

本脚本：解码 0x506b20/0x506ba0 两张资源表、扫描全镜像枚举所有 *.LZW/*.PK8 资源阵列、
验证 type-0/type-1 handler 簇→资源表链接、GBK 解码 0x50d820/0x50d834 消息串。
"""
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

import os, struct, re
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

BASE = 0x400000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(ROOT, 'scripts', _ROOT + '/scripts/_unpacked_mem.bin'), 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

# 已知资源表（续160/161 实锤）
KNOWN_TABLES = {
    0x506b20: ('type-0 簇 (0x492e20)', 'B:MAPCHIP.LZW 等 6 项'),
    0x506ba0: ('type-1 簇 (0x492ed0)', 'C:TOWNCHIP.LZW 等 6 项'),
}


def gbk(b: bytes) -> str:
    try:
        return b.decode('cp936', errors='replace')
    except Exception:
        return b.decode('latin1', errors='replace')


def decode_filename_table(va, maxn=32, stride=16):
    """解码资源文件名表：每条 16B（≤14 字符名 + NUL + 填充），stride 16。

    名称字段占 16B 记录内 [0:15]，NUL 终止（最长 B:SHOP_OBJ.LZW=14 字符）。
    故解码窗口取 15 字节并 rstrip(b'\\x00')，且须先判 chunk[0]==0 才 break（首字节
    即 NUL = 表结束哨兵），不能用 13 字节窗口（会截断 14 字符长名致正则失败提前 break）。
    """
    out = []
    for i in range(maxn):
        off = va - BASE + i * stride
        if off + 15 > len(MEM):
            break
        chunk = MEM[off: off + 15]
        if chunk[0] == 0:
            break
        s = gbk(chunk.rstrip(b'\x00'))
        if not re.match(r'^[A-Za-z]:[\\/]?[\w.]+\.(LZW|PK8|LZ2|TR2)$', s):
            break
        out.append(s)
    return out


def dis(va, n):
    return list(md.disasm(MEM[va - BASE: va - BASE + n], va))


def txts(va, n):
    return [f'{i.mnemonic} {i.op_str}'.strip() for i in dis(va, n)]


def fn_len(va, maxb=0x600):
    n = 0
    for i in dis(va, maxb):
        n += i.size
        if i.mnemonic == 'ret':
            return n
    return maxb


def scan_resource_arrays():
    """扫描全镜像：找所有「连续 N 个 'X:NAME.LZW'/'X:NAME.PK8'（16B 对齐）」阵列。

    名称字段 ≤14 字符 + NUL + 填充，故每条取完整 16B、取 [0:15] rstrip NUL 得名称，
    并以 chunk[len(name)]==0 确认紧邻 NUL 终止（避免 13 字节窗口越界 IndexError /
    14 字符长名截断）。
    """
    pat = re.compile(rb'^[A-Z]:[\\/]?[\w.]+\.(LZW|PK8|LZ2|TR2)$')
    hits = []
    off = 0
    STRIDE = 16
    while off + STRIDE <= len(MEM):
        chunk = MEM[off: off + STRIDE]
        name = chunk[:15].rstrip(b'\x00')
        if 1 <= len(name) <= 15 and pat.match(name) and chunk[len(name)] == 0:
            n = 0
            while True:
                o2 = off + n * STRIDE
                if o2 + STRIDE > len(MEM):
                    break
                c2 = MEM[o2: o2 + STRIDE]
                s2 = c2[:15].rstrip(b'\x00')
                if 1 <= len(s2) <= 15 and pat.match(s2) and c2[len(s2)] == 0:
                    n += 1
                else:
                    break
            if n >= 3:
                names = [gbk(MEM[off + i * STRIDE: off + i * STRIDE + 15].rstrip(b'\x00')) for i in range(n)]
                hits.append((BASE + off, n, names))
                off += n * STRIDE
                continue
        off += 1
    return hits


def _run_tests():
    ok = []
    def chk(name, cond, extra=''):
        ok.append(bool(cond))
        print(f'  [{"OK" if cond else "FAIL"}] {name}{(" — " + extra) if extra else ""}')

    print('--- T1 资源表 0x506b20 / 0x506ba0 解码（16B 对齐文件名阵列）---')
    t0 = decode_filename_table(0x506b20)
    chk('0x506b20 = 6 个资源名', len(t0) == 6, str(t0))
    chk('0x506b20 含 MAPCHIP.LZW', 'B:MAPCHIP.LZW' in t0)
    chk('0x506b20 含 ANMSEQ.LZW', 'B:ANMSEQ.LZW' in t0)
    t1 = decode_filename_table(0x506ba0)
    chk('0x506ba0 = 6 个资源名', len(t1) == 6, str(t1))
    chk('0x506ba0 含 TOWNCHIP.LZW', 'C:TOWNCHIP.LZW' in t1)
    chk('0x506ba0 含 HEXMES.LZW', 'C:HEXMES.LZW' in t1)

    print('--- T2 handler 簇 → 资源表 链接（type-0→0x506b20 / type-1→0x506ba0）---')
    t = txts(0x492E20, fn_len(0x492E20))
    chk('0x492e20 (type-0) push 0x506b20', 'push 0x506b20' in t)
    t = txts(0x492ED0, fn_len(0x492ED0))
    chk('0x492ed0 (type-1) push 0x506ba0', 'push 0x506ba0' in t)

    print('--- T3 选择器构造器 0x4ec8c0（selector&0xfb, mod4→尺寸 0/1/2/0x1000, 经 [0x4fb07c] 注册）---')
    t = txts(0x4EC8C0, fn_len(0x4EC8C0))
    chk('and al, 0xfb（掩码）', 'and al, 0xfb' in t)
    chk('cmp eax, 3 + ja（4 路 switch）', 'cmp eax, 3' in t)
    chk('调用 [0x4fb07c]（登记/分配器）', 'call dword ptr [0x4fb07c]' in t)
    chk('尺寸 0/1/2/0x1000 三态', 'push 0' in t and 'push 1' in t and 'push 2' in t and 'push 0x1000' in t)

    print('--- T4 资源登记 0x492800 → 0x4f40b0（3 参转发）---')
    t = txts(0x492800, 0x20)
    chk('0x492800 call 0x4f40b0', 'call 0x4f40b0' in t)

    print('--- T5 0x50d820 / 0x50d834 是 GBK 消息串（非类型模板）---')
    def gb(va, n=0x30):
        return gbk(MEM[va - BASE: va - BASE + n].split(b'\x00')[0])
    m0 = gb(0x50D820)
    m1 = gb(0x50D834)
    chk('0x50d820 解 GBK 非空', len(m0) > 0, m0)
    chk('0x50d834 解 GBK 非空', len(m1) > 0, m1)
    # 含中文字符（cp936 多字节）→ 非 ASCII 模板
    chk('含中文字符（武器/等）', any(ord(c) > 0x4e00 for c in m0 + m1), f'{m0!r} / {m1!r}')

    print('--- T6 全镜像资源阵列枚举（类别资源表全集）---')
    arrs = scan_resource_arrays()
    chk('枚举到 >=2 张资源阵列', len(arrs) >= 2, f'{len(arrs)} 张')
    # 注意：0x506b20 / 0x506ba0 在二进制里是 *更大连续阵列的内嵌条目*，不是阵列起点：
    #   0x506b20 = 阵列 0x506ac0(12项 MMLDATA..ANMSEQ) 的内嵌 [6..11]
    #   0x506ba0 = 阵列 0x506b90(7项 PK8DATA..EXTFACE)  的内嵌 [1..6]
    # 故验证「扫描阵列的字节区间覆盖这两个表基址」，而非「阵列起点等于它们」。
    cover0 = any(a[0] <= 0x506b20 < a[0] + a[1] * 16 for a in arrs)
    cover1 = any(a[0] <= 0x506ba0 < a[0] + a[1] * 16 for a in arrs)
    chk('枚举阵列覆盖 0x506b20 (type-0 表)', cover0)
    chk('枚举阵列覆盖 0x506ba0 (type-1 表)', cover1)
    print('    资源阵列清单（地址: 项数: 首3项）:')
    for va, n, names in sorted(arrs)[:12]:
        mark0 = '  ←含0x506b20' if va <= 0x506b20 < va + n * 16 else ''
        mark1 = '  ←含0x506ba0' if va <= 0x506ba0 < va + n * 16 else ''
        print(f'      0x{va:06x}: {n} 项  {names[:3]}{mark0}{mark1}')

    n = sum(ok)
    print(f'\nRESULT: {n}/{len(ok)} checks passed')
    return n == len(ok)


if __name__ == '__main__':
    import sys
    sys.exit(0 if _run_tests() else 1)
