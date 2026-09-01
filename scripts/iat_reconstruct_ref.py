#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
iat_reconstruct_ref.py -- 续209：未解析 IAT 全量重建（121 个 Win32 API 槽逐一命名）
=====================================================================================
🔑 **突破**：`0x4fb000..0x4fb1f4` 不是「运行期回调槽」，而是**本镜像未解析的导入地址表
(IAT)**。壳把 121 个槽全填成占位常量 `0x3000`（4 个 DLL 分组的 NULL 分隔符 + 1 个尾部
padding 保持为 0），但**原始 hint-name blob 完好保留在 `0x530007..0x53072e`**，于是可以
把 121 个槽逐一还原成 Win32 API 名。

判据（四重独立互证，全部在本脚本里断言）：
  ① **计数精确相等**：name blob 解出 121 个 IMAGE_IMPORT_BY_NAME，IAT 里 == 0x3000 的
     槽恰好 121 个。
  ② **NULL 分隔符落点精确**：按 DLL 分组累加得到的边界 slot（26 / 82 / 121 / 124）在
     镜像里恰好 == 0（IAT 每个 DLL 的 thunk 数组以 NULL 结尾）。
  ③ **既有 emu 桩反查全中**：续202/续208 靠「参数形状」盲试出来的 4 个槽，重建后名字与
     参数个数全对上 ——
        `[0x4fb0a0]`(slot 40) = `_lread`   (h, buf, cnt)  3 args ⇒ ret 0xc  ✔ 续202
        `[0x4fb0a8]`(slot 42) = `_llseek`  (h, off, org)  3 args            ✔ 续208
        `[0x4fb09c]`(slot 39) = `_lclose`  (h)            1 arg             ✔ 续208
        `[0x4fb07c]`(slot 31) = `OpenFile` (name, of, mode) 3 args          ✔ 续208
  ④ **调用点参数个数与 API 原型逐一吻合**（Win32 消息泵，见下）。

🆕 **附带定名两个核心运行期函数**（续208 emu 里打到裸 0x3000 的 6 个调用点全部解释清）：
  * `0x4f1ef8` = **Win32 消息泵** `PumpMessages()`
        `PeekMessageA(&msg,0,0,0,PM_REMOVE)` → 若有消息 → `TranslateMessage(&msg)`
        + `DispatchMessageA(&msg)`；局部 `[ebp-0x1c]` 正是 28 字节 MSG 结构。
  * `0x4f1fcb` = **鼠标轮询** `PollMouse()`：先 call 0x4f1ef8 抽消息，再
        `GetCursorPos(&pt)`(POINT=8B, 局部 [ebp-8]) → `ScreenToClient(hWnd,&pt)`
        （hWnd 取自窗口句柄表 `[0x52b5b8 + 4*[0x52c5a8]]`）⇒ 得客户区坐标。
  * `0x491f58` 是 vtable thiscall `call [[esi+0x96]+0x10]`（非 IAT），pop=0。

📌 **emu 通则（沉淀）**：本镜像所有 `call dword ptr [0x4fbXXX]` 都是 Win32 API 调用。
   emu 要么整页桩 `0x3000` 为 `ret`，要么按本脚本产出的 `iat_map.json` 把槽逐个重定向到
   语义桩。**不要再把它们当「未知运行期回调」绕过**。
"""
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))

import os, sys, struct, json, collections, re
sys.path.insert(0, os.path.join(_ROOT, 'scripts'))
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from _disasm_all import disasm_all

BASE = 0x400000
MEM = open(os.path.join(_ROOT, 'scripts', '_unpacked_mem.bin'), 'rb').read()

IAT_LO, IAT_HI = 0x4fb000, 0x4fb1f8        # [lo, hi)  —— 0x4fb1f8 起是 C++ vtable 表区
NAME_BLOB_LO, NAME_BLOB_HI = 0x530007, 0x530730
FILL = 0x3000                              # 壳的未解析占位常量

# IAT 里 DLL 分组的实际顺序（与壳自己重写的描述符表顺序不同 —— 由 NULL 分隔符定死）
DLL_ORDER = ['GDI32.dll', 'KERNEL32.DLL', 'USER32.dll', 'WINMM.dll']

# 名字 blob 里各 DLL 组的起始地址（由组首 API 定位）
GROUP_FIRST = {
    'KERNEL32.DLL': 'ExitProcess',
    'GDI32.dll': 'GetDeviceCaps',
    'USER32.dll': 'InvalidateRect',
    'WINMM.dll': 'mciSendCommandA',
}


def u32(va):
    return struct.unpack('<I', MEM[va - BASE:va - BASE + 4])[0]


def parse_name_blob():
    """扫 hint-name blob，按出现顺序返回 [(va, name)]。"""
    seg = MEM[NAME_BLOB_LO - BASE:NAME_BLOB_HI - BASE]
    out = []
    for m in re.finditer(rb'[A-Za-z_][A-Za-z0-9_]{3,60}\x00', seg):
        out.append((NAME_BLOB_LO + m.start(), m.group()[:-1].decode('ascii')))
    return out


def group_names(names):
    """按 GROUP_FIRST 把 blob 切成 4 个 DLL 组（blob 内组是连续的）。"""
    idx = {}
    for i, (_, nm) in enumerate(names):
        for dll, first in GROUP_FIRST.items():
            if nm == first and dll not in idx:
                idx[dll] = i
    bounds = sorted((i, dll) for dll, i in idx.items())
    groups = {}
    for k, (i, dll) in enumerate(bounds):
        j = bounds[k + 1][0] if k + 1 < len(bounds) else len(names)
        groups[dll] = [nm for _, nm in names[i:j]]
    return groups


def build_iat_map(groups):
    """按 DLL_ORDER 铺进 IAT，每组后跟一个 NULL 槽。返回 (slot->名, NULL 槽列表)。"""
    m, nulls, slot = {}, [], 0
    for dll in DLL_ORDER:
        for nm in groups[dll]:
            m[slot] = (dll, nm)
            slot += 1
        nulls.append(slot)
        slot += 1
    return m, nulls


def main():
    tests = []

    def T(name, ok, detail=''):
        tests.append((name, bool(ok), detail))
        print('  %s %s%s' % ('PASS' if ok else 'FAIL', name, ('  — ' + detail) if detail else ''))

    print('=' * 78)
    print('A. IAT 区形态（121 槽全为占位常量 0x3000 + NULL 分隔）')
    print('=' * 78)
    slots = [(va, u32(va)) for va in range(IAT_LO, IAT_HI, 4)]
    fills = [va for va, v in slots if v == FILL]
    zeros = [va for va, v in slots if v == 0]
    others = [(va, v) for va, v in slots if v not in (FILL, 0)]
    print('  槽总数=%d  占位(0x3000)=%d  NULL=%d  其他=%d'
          % (len(slots), len(fills), len(zeros), len(others)))
    T('IAT 区无已解析地址（全是 0x3000 或 0）', not others, str(others[:3]))
    T('0x4fb1f8 起已是 vtable 区（值落在代码段 0x40xxxx-0x4fxxxx）',
      0x400000 < u32(0x4fb1f8) < 0x4fb000, '0x%08x' % u32(0x4fb1f8))

    print()
    print('=' * 78)
    print('B. hint-name blob 解析 + 分组')
    print('=' * 78)
    names = parse_name_blob()
    groups = group_names(names)
    tot = sum(len(v) for v in groups.values())
    for dll in DLL_ORDER:
        print('  %-14s %3d 个: %s ... %s' % (dll, len(groups[dll]), groups[dll][0], groups[dll][-1]))
    print('  合计 %d' % tot)
    T('① 名字个数 == 占位槽个数（121）', tot == len(fills), '%d vs %d' % (tot, len(fills)))

    imap, nulls = build_iat_map(groups)
    null_vas = [IAT_LO + 4 * s for s in nulls]
    print('  推导 NULL 分隔槽: %s' % ['0x%06x' % v for v in null_vas])
    T('② NULL 分隔符落点全部命中（4/4）',
      all(u32(v) == 0 for v in null_vas),
      str([('0x%06x' % v, '0x%x' % u32(v)) for v in null_vas]))
    T('② 全部占位槽都被命名（无遗漏/无越界）',
      set(IAT_LO + 4 * s for s in imap) == set(fills),
      'named=%d fills=%d' % (len(imap), len(fills)))

    print()
    print('=' * 78)
    print('C. 反查续202/续208 盲试出来的 4 个 emu 桩（名字 + 参数个数须自洽）')
    print('=' * 78)
    # (槽VA, 期望API, 期望栈参个数)
    KNOWN = [(0x4fb0a0, '_lread', 3), (0x4fb0a8, '_llseek', 3),
             (0x4fb09c, '_lclose', 1), (0x4fb07c, 'OpenFile', 3)]
    for va, want, nargs in KNOWN:
        s = (va - IAT_LO) // 4
        got = imap.get(s, ('?', '?'))[1]
        T('③ [0x%06x] (slot %d) = %s' % (va, s, want), got == want, got)

    print()
    print('=' * 78)
    print('D. 调用点参数个数 vs API 原型（Win32 消息泵 / 鼠标轮询）')
    print('=' * 78)
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True

    def push_count_before(call_va, window=0x40):
        """数 call 之前连续 push 段的 push 条数（遇非 push/lea/mov/xor 之类停）。

        ⚠️ 两重坑，缺一不可（实测 ScreenToClient 因此从 0 → 2）：
          1) **capstone ≥5 的 `md.skipdata=True` 会静默截断**（续205）：遇非法字节直接
             停止迭代，既不抛异常也不跳过 —— 旧写法在 0x4f1fc0 起点返回 0 条指令。
             ⇒ 必须走 `_disasm_all.disasm_all` 的「遇非法字节前进 1 字节重启」循环。
          2) **x86 变长指令不能从单一固定起点反汇编**（必错位）⇒ 在 disasm_all 产出的
             指令流里，**反向定位「address + size == call_va」的那一条**作为锚点（边界
             对齐），再从它往前逐条回溯；并全程校验指令边界连续。
        """
        lo = call_va - window
        seq = list(disasm_all(md, MEM[lo - BASE:call_va - BASE], lo))
        # 锚点：以 call_va 结尾的那条指令
        k = None
        for idx, ins in enumerate(seq):
            if ins.address + ins.size == call_va:
                k = idx
        if k is None:
            return -1
        n = 0
        prev_end = call_va          # 从锚点本身开始数（含 k 那条）
        for idx in range(k, -1, -1):
            ins = seq[idx]
            if ins.address + ins.size != prev_end:   # 指令边界不连续 → 断链
                break
            if ins.mnemonic == 'push':
                n += 1
            elif ins.mnemonic in ('lea', 'mov', 'xor', 'movzx', 'movsx'):
                prev_end = ins.address
                continue
            else:
                break
            prev_end = ins.address
        return n

    # (call 指令 VA, IAT 槽 VA, 期望 API, 期望栈参个数)
    SITES = [
        (0x4f1f09, 0x4fb1d8, 'PeekMessageA', 5),
        (0x4f1f17, 0x4fb1a8, 'TranslateMessage', 1),
        (0x4f1f21, 0x4fb1a4, 'DispatchMessageA', 1),
        (0x4f1fda, 0x4fb1d0, 'GetCursorPos', 1),
        (0x4f1ff0, 0x4fb1d4, 'ScreenToClient', 2),
    ]
    for cva, sva, want, nargs in SITES:
        s = (sva - IAT_LO) // 4
        got = imap.get(s, ('?', '?'))[1]
        pc = push_count_before(cva)
        T('④ 0x%06x call [0x%06x] = %s (%d 参)' % (cva, sva, want, nargs),
          got == want and pc == nargs, '名=%s push=%d' % (got, pc))

    T('0x4f1ef8 局部 MSG 结构 = 0x1c(28B)',
      MEM[0x4f1efb - BASE:0x4f1efb - BASE + 3] == b'\x83\xec\x1c')
    T('0x4f1fcb 先 call 消息泵 0x4f1ef8',
      MEM[0x4f1fd1 - BASE] == 0xe8 and
      (0x4f1fd6 + struct.unpack('<i', MEM[0x4f1fd2 - BASE:0x4f1fd6 - BASE])[0]) == 0x4f1ef8)
    T('0x491f58 是 vtable thiscall（call [eax+0x10]，非 IAT）',
      MEM[0x491f58 - BASE:0x491f58 - BASE + 3] == b'\xff\x50\x10')

    print()
    print('=' * 78)
    print('E. 全镜像 call [0x4fbXXX] 调用点统计（子系统画像）')
    print('=' * 78)
    md2 = Cs(CS_ARCH_X86, CS_MODE_32)
    cnt = collections.Counter()
    sites = collections.defaultdict(list)
    data = MEM[0x401000 - BASE:]
    nins = 0
    for ins in disasm_all(md2, data, 0x401000):
        nins += 1
        if ins.mnemonic == 'call' and ins.op_str.startswith('dword ptr ['):
            m = re.match(r'dword ptr \[(0x[0-9a-f]+)\]$', ins.op_str)
            if m:
                sva = int(m.group(1), 16)
                if IAT_LO <= sva < IAT_HI:
                    s = (sva - IAT_LO) // 4
                    nm = imap.get(s, ('?', '<null slot>'))[1]
                    cnt[nm] += 1
                    if len(sites[nm]) < 6:
                        sites[nm].append(ins.address)
    print('  全镜像 %d 条指令，IAT 间接调用点 %d 处，覆盖 %d 个 API'
          % (nins, sum(cnt.values()), len(cnt)))
    T('全镜像扫描未被截断（续205 补丁生效，>80 万条）', nins > 800000, str(nins))
    T('IAT 调用点 > 300 处（证明 0x4fbXXX 确是热点 API 表）', sum(cnt.values()) > 300,
      str(sum(cnt.values())))
    print('\n  TOP 30 被调 API:')
    for nm, n in cnt.most_common(30):
        print('    %-26s x%-4d  例: %s' % (nm, n, ', '.join('0x%06x' % a for a in sites[nm][:4])))

    # 子系统画像断言（这些 API 存在即定死引擎技术栈）
    allnames = set(nm for _, nm in imap.values())
    T('图形栈 = GDI 8-bit 调色板 DIB（CreateDIBSection/SetDIBColorTable/AnimatePalette/BitBlt）',
      {'CreateDIBSection', 'SetDIBColorTable', 'AnimatePalette', 'BitBlt'} <= allnames)
    T('文字栈 = GDI 字体（CreateFontA/TextOutA/GetTextMetricsA）',
      {'CreateFontA', 'TextOutA', 'GetTextMetricsA'} <= allnames)
    T('音乐栈 = MCI（mciSendCommandA，对应 Taikou2 Original 的 34 个 mp3）',
      'mciSendCommandA' in allnames)
    T('计时栈 = timeGetTime + GetTickCount', {'timeGetTime', 'GetTickCount'} <= allnames)
    T('文件栈 = 16-bit 风格 OpenFile/_lread/_llseek/_lclose/_lwrite（非 CreateFileA）',
      {'OpenFile', '_lread', '_llseek', '_lclose', '_lwrite'} <= allnames
      and 'CreateFileA' not in allnames)
    T('无 DirectX / DirectSound 导入（纯 GDI + MCI）',
      not any(x.startswith('Direct') or x.startswith('DD') or x.startswith('DS')
              for x in allnames))

    out = {
        'iat_range': ['0x%06x' % IAT_LO, '0x%06x' % IAT_HI],
        'fill_const': '0x%x' % FILL,
        'name_blob': ['0x%06x' % NAME_BLOB_LO, '0x%06x' % NAME_BLOB_HI],
        'dll_order_in_iat': DLL_ORDER,
        'null_separator_slots': ['0x%06x' % v for v in null_vas],
        'slots': {('0x%06x' % (IAT_LO + 4 * s)): {'slot': s, 'dll': d, 'api': n}
                  for s, (d, n) in sorted(imap.items())},
        'call_site_counts': dict(cnt.most_common()),
        'call_site_examples': {k: ['0x%06x' % a for a in v] for k, v in sites.items()},
        'named_functions': {
            '0x4f1ef8': 'PumpMessages() — PeekMessageA/TranslateMessage/DispatchMessageA',
            '0x4f1fcb': 'PollMouse() — PumpMessages + GetCursorPos + ScreenToClient',
        },
    }
    outp = os.path.join(_ROOT, 'scripts', 'iat_map.json')
    with open(outp, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print('\nJSON ->', outp)

    npass = sum(1 for _, ok, _ in tests if ok)
    print('RESULT: %d/%d' % (npass, len(tests)))
    bad = [n for n, ok, _ in tests if not ok]
    assert not bad, '失败项: %s' % bad
    print('ALL PASS ✅  IAT 121 槽全命名 + 消息泵/鼠标轮询定名')


if __name__ == '__main__':
    main()
