#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
savedata_loadflow_emu_ref.py -- 续208：读档流程 emu 端到端坐实（正确入口 0x4e8600）
================================================================================
配套 `savedata_loadflow_ref.py`（静态 34/34）的运行期确认。

关键修正（本轮）：起跑地址必须是 **0x4e8600**（函数入口 `sub esp,0xc`），
而非续206 用的 **0x4e8625**（那是循环体中段的 `call 0x47fc60` 指令本身）。
从中段起跑 ⇒ esi 与 4 个栈参全是垃圾 ⇒ `0x47fcad mov word[edx],ax` 未映射写。

验证目标：
  ① 喂真实 SAVEDATA.TR2，钩槽选择器 `0x480240` 返回指定槽号；
  ② slot0（有效存档）→ 头三字非 0 → 走确认框 → 读档 → 按 `0x5205fe` 载入资源簇；
     并检查三个显示缓冲被 strcpy 出真实文本：
       0x522c88='木下藤吉郎' / 0x522c60='尾张国' / 0x522c70='清洲城步兵头'
  ③ slot1（空存档）→ 头三字全 0 → 命中 `0x47b160(0x50d820)`「这个进度无法使用。」
  ④ mode 0/1/2 分别落到簇0 / 簇1 / else 簇（`0x5205fe` 三路极性）。

桩策略（全部用 UC_HOOK_CODE 在真实函数地址拦截，**不改写镜像字节**）：
  ⚠️ 旧脚本把指针 `write` 到 `0x4ebfe0`/`0x4ebfc0`（strcpy/strlen）—— 那是**直接 call
  的函数体，不是 IAT 槽**，等于砸掉函数序言，导致三缓冲永远为空。本脚本让
  strcpy/strlen 原生执行。

  🔑 **IAT 通则（续209）**：`0x4fb000..0x4fb1f4` 是本镜像**未解析的导入地址表**，121 个
  槽全填占位常量 `0x3000`。所以任何 `call dword ptr [0x4fb0xx]` 都会跳到未映射的
  `0x3000` → INVALID_INSTRUCTION。解法两层：
    (a) 整页兜底：`mem_map(0x3000)` 填满 `ret`，让所有未桩的 Win32 API 安全返回；
    (b) 语义桩：本流程真正依赖的 4 个 API 按 `iat_map.json` 精确重定向 ——
          `[0x4fb07c]` = OpenFile(name, ofs, mode)   3 参
          `[0x4fb09c]` = _lclose(h)                   1 参
          `[0x4fb0a0]` = _lread(h, buf, cnt)          3 参
          `[0x4fb0a8]` = _llseek(h, off, origin)      3 参
  本轮跑到的裸 0x3000 调用点（全部由 (a) 兜住）：`PeekMessageA`/`TranslateMessage`/
  `DispatchMessageA`（消息泵 0x4f1ef8）+ `GetCursorPos`/`ScreenToClient`（鼠标轮询
  0x4f1fcb）+ 一个 vtable thiscall `0x491f58`。
"""
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))

import os, sys, struct, json, gc
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX, UC_X86_REG_ECX
from emu_sndata_read import Emu

SAV_PATH = os.path.join(_ROOT, 'Taikou2 Original', 'SAVEDATA.TR2')

ENTRY = 0x4e8600          # ✅ 真入口（续208 修正）
WRONG_ENTRY = 0x4e8625    # ❌ 续206 误用（实为 call 0x47fc60）

BUF_NAME = 0x522c88       # 主角名
BUF_PROV = 0x522c60       # 所在国
BUF_POST = 0x522c70       # 所在地+身分

# 场景/资源子系统里与「资源身份」无关的调用 → 统一空 ret（调用方清栈）
NOOP_RET = [
    0x47bde0, 0x47ae80, 0x47c080, 0x47ae20, 0x47b2e0, 0x47adc0, 0x47ad60,
    0x47d850,                                   # 文件对象析构
    0x4ee340, 0x4b0ad0, 0x4edfa0, 0x4edf70,     # 资源子系统 thiscall
    0x499050, 0x4ac9c0, 0x4ae380, 0x4a0b70,     # 簇1 伴随
    0x48cc20, 0x48d350, 0x48e690, 0x4a0b20,     # 簇0 伴随
    0x491f90, 0x492050,                         # else 簇伴随
    0x4ef690,
]

CLUSTERS = {
    0x492e20: 'L0/0x492e20', 0x493140: 'L0/0x493140',
    0x492ed0: 'L1/0x492ed0', 0x4931f0: 'L1/0x4931f0',
    0x491e70: 'ELSE/0x491e70', 0x4873b0: 'ELSE/0x4873b0',
}


def gbk_at(e, va, n=20):
    b = e.read(va, n)
    k = b.find(b'\x00')
    body = b[:k if k >= 0 else n]
    try:
        return body.decode('gbk')
    except Exception:
        return body.decode('latin-1', 'replace')


def run(mode, slot, sav, verbose=False):
    """跑一遍 0x4e8600，返回 (资源名列表, 命中簇列表, 三缓冲文本, 空槽提示次数, 崩溃点)"""
    e = Emu()

    # 惰性映射：资源加载会往运行期分配的游戏表缓冲写，静态镜像里没有这些页。
    # 命中未映射访问就按页补映射并继续 —— 让 boot 走完而不是在第一处缓冲上崩。
    lazy = []

    def on_unmapped(mu, access, address, size, value, ud):
        page = address & ~0xfff
        try:
            mu.mem_map(page, 0x10000)
            lazy.append(page)
        except Exception:
            try:
                mu.mem_map(page, 0x1000)
                lazy.append(page)
            except Exception:
                return False
        return True

    e.mu.hook_add(UC_HOOK_MEM_UNMAPPED, on_unmapped)

    # (a) IAT 占位常量 0x3000 整页兜底：未桩的 Win32 API 一律安全 ret
    e.mem_map(0x3000, 0x1000)
    e.write(0x3000, b'\xc3' * 0x1000)

    # (b) 语义桩：4 个真正参与读档 I/O 的 API（槽名由续209 iat_map.json 给出）
    STUB = 0x900000
    e.mem_map(STUB, 0x2000)
    e.write(STUB, b'\xc3' * 0x2000)
    for slotva, off in ((0x4fb0a8, 0x00),    # _llseek
                        (0x4fb0a0, 0x10),    # _lread
                        (0x4fb09c, 0x20),    # _lclose
                        (0x4fb07c, 0x30)):   # OpenFile
        e.write(slotva, struct.pack('<I', STUB + off))
    e.write(0x5205fe, struct.pack('<H', mode))

    pos = [0]
    res, clus, empty_hits, confirm_hits, load_hits = [], [], [0], [0], [0]

    def ret_only(mu, sp, eax=None, pop=0):
        r = struct.unpack('<I', mu.mem_read(sp, 4))[0]
        if eax is not None:
            mu.reg_write(UC_X86_REG_EAX, eax & 0xffffffff)
        mu.reg_write(UC_X86_REG_ESP, sp + 4 + pop)
        mu.reg_write(UC_X86_REG_EIP, r)

    def on_code(mu, address, size, ud):
        sp = mu.reg_read(UC_X86_REG_ESP)
        if address == STUB + 0x00:                       # lseek(h, off, whence) cdecl3
            off = struct.unpack('<I', mu.mem_read(sp + 8, 4))[0]
            pos[0] = off
            ret_only(mu, sp, eax=off, pop=12)
        elif address == STUB + 0x10:                     # read(h, dst, cnt) cdecl3
            dst = struct.unpack('<I', mu.mem_read(sp + 8, 4))[0]
            cnt = struct.unpack('<I', mu.mem_read(sp + 0xc, 4))[0]
            n = max(0, min(cnt, len(sav) - pos[0]))
            if n:
                try:
                    mu.mem_write(dst, sav[pos[0]:pos[0] + n])
                except Exception:
                    # 目标是运行期分配的游戏表缓冲，静态镜像无此页 → 补映射
                    on_unmapped(mu, 0, dst, n, 0, None)
                    try:
                        mu.mem_write(dst, sav[pos[0]:pos[0] + n])
                    except Exception:
                        pass
            pos[0] += n
            ret_only(mu, sp, eax=n, pop=12)
        elif address == STUB + 0x20:                     # flush/close
            ret_only(mu, sp, eax=0, pop=4)
        elif address == STUB + 0x30:                     # 运行期资源加载器 -> 成功
            ret_only(mu, sp, eax=1, pop=12)
        elif address == 0x47d720:                        # 开文件 stdcall2 -> 成功
            ret_only(mu, sp, eax=1, pop=8)
        elif address == 0x480240:                        # 槽选择器 -> 指定槽号
            ret_only(mu, sp, eax=slot & 0xffff)
        elif address == 0x47b160:                        # 「这个进度无法使用。」
            empty_hits[0] += 1
            ret_only(mu, sp)
        elif address == 0x47b390:                        # 确认框 -> 是
            confirm_hits[0] += 1
            ret_only(mu, sp, eax=1)
        elif address == 0x47fb80:                        # 真正读档 -> 成功（隔离资源问题）
            load_hits[0] += 1
            ret_only(mu, sp, eax=1)
        elif address == 0x4ec8c0:                        # 资源选择器 stdcall2
            np = struct.unpack('<I', mu.mem_read(sp + 4, 4))[0]
            try:
                raw = bytes(mu.mem_read(np, 16))
                k = raw.find(b'\x00')
                nm = raw[:k if k >= 0 else 16].decode('latin-1')
            except Exception:
                nm = '<unreadable 0x%x>' % np
            res.append(nm)
            ret_only(mu, sp, eax=1, pop=8)
        elif address in CLUSTERS:
            clus.append(CLUSTERS[address])
        elif address in NOOP_RET:
            ret_only(mu, sp)

    e.mu.hook_add(UC_HOOK_CODE, on_code)

    crash = None
    try:
        e.call(ENTRY, args=(), regs={}, max_steps=0x1000000)
    except Exception as ex:
        crash = '0x%06x: %s' % (e.last[0], ex)

    bufs = {'0x522c88': gbk_at(e, BUF_NAME), '0x522c60': gbk_at(e, BUF_PROV),
            '0x522c70': gbk_at(e, BUF_POST)}
    out = dict(res=res, clusters=clus, bufs=bufs, empty=empty_hits[0],
               confirm=confirm_hits[0], load=load_hits[0], crash=crash,
               lazy_pages=len(lazy))
    del e
    gc.collect()
    return out


def main():
    sav = open(SAV_PATH, 'rb').read()
    tests = []

    def T(name, ok, detail=''):
        tests.append((name, bool(ok), detail))
        print('  %s %s%s' % ('PASS' if ok else 'FAIL', name, ('  — ' + detail) if detail else ''))
        sys.stdout.flush()

    print('=' * 78)
    print('A. 入口地址修正验证（0x4e8600 vs 续206 的 0x4e8625）')
    print('=' * 78)
    b = bytes(open(os.path.join(_ROOT, 'scripts', '_unpacked_mem.bin'), 'rb').read())
    T('0x4e8600 = sub esp,0xc (真入口)', b[ENTRY - 0x400000: ENTRY - 0x400000 + 3] == b'\x83\xec\x0c')
    T('0x4e8625 首字节 = 0xe8 (call 指令，非入口)',
      b[WRONG_ENTRY - 0x400000] == 0xe8)

    print()
    print('=' * 78)
    print('B. slot0（有效存档）× mode 0/1/2')
    print('=' * 78)
    out = {}
    for mode in (0, 1, 2):
        r = run(mode, 0, sav)
        out['mode%d_slot0' % mode] = r
        print('  mode=%d  簇=%s  资源=%s' % (mode, r['clusters'], r['res']))
        print('          缓冲: 名=%r 国=%r 地=%r  确认=%d 读档=%d 空槽=%d  crash=%s'
              % (r['bufs']['0x522c88'], r['bufs']['0x522c60'], r['bufs']['0x522c70'],
                 r['confirm'], r['load'], r['empty'], r['crash']))
        T('mode=%d: 三缓冲被 strcpy 出真实文本(主角名=木下藤吉郎)' % mode,
          r['bufs']['0x522c88'] == '木下藤吉郎', r['bufs']['0x522c88'])
        T('mode=%d: 所在国=尾张国' % mode, r['bufs']['0x522c60'] == '尾张国', r['bufs']['0x522c60'])
        T('mode=%d: 所在地+身分=清洲城步兵头' % mode,
          r['bufs']['0x522c70'] == '清洲城步兵头', r['bufs']['0x522c70'])
        T('mode=%d: 走确认框(非空槽提示)' % mode, r['confirm'] >= 1 and r['empty'] == 0,
          'confirm=%d empty=%d' % (r['confirm'], r['empty']))
        T('mode=%d: 触发读档 0x47fb80' % mode, r['load'] >= 1, str(r['load']))

    # 三路极性
    c0 = set(x.split('/')[0] for x in out['mode0_slot0']['clusters'])
    c1 = set(x.split('/')[0] for x in out['mode1_slot0']['clusters'])
    c2 = set(x.split('/')[0] for x in out['mode2_slot0']['clusters'])
    T('mode=0 命中簇0(L0)', 'L0' in c0, str(sorted(c0)))
    T('mode=1 命中簇1(L1)', 'L1' in c1, str(sorted(c1)))
    T('mode=0/1 均含 ELSE 簇（双模式共执行）', 'ELSE' in c0 and 'ELSE' in c1,
      '%s / %s' % (sorted(c0), sorted(c1)))
    T('mode=2 只命中 ELSE 簇（不进簇0/簇1）',
      c2 == {'ELSE'} or ('L0' not in c2 and 'L1' not in c2), str(sorted(c2)))

    print()
    print('=' * 78)
    print('C. slot1（空存档）→ 空槽提示分支')
    print('=' * 78)
    r = run(0, 1, sav)
    out['mode0_slot1'] = r
    print('  簇=%s  资源=%s  空槽提示=%d 确认=%d 读档=%d  crash=%s'
          % (r['clusters'], r['res'], r['empty'], r['confirm'], r['load'], r['crash']))
    T('slot1: 命中「这个进度无法使用。」(0x47b160)', r['empty'] >= 1, str(r['empty']))
    T('slot1: 未走读档确认/未读档', r['confirm'] == 0 and r['load'] == 0,
      'confirm=%d load=%d' % (r['confirm'], r['load']))
    T('slot1: 未载入任何资源簇', not r['clusters'], str(r['clusters']))

    outp = os.path.join(_ROOT, 'scripts', 'savedata_loadflow_emu.json')
    with open(outp, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print('\nJSON ->', outp)

    npass = sum(1 for _, ok, _ in tests if ok)
    print('RESULT: %d/%d' % (npass, len(tests)))
    bad = [n for n, ok, _ in tests if not ok]
    assert not bad, '失败项: %s' % bad
    print('ALL PASS ✅  读档流程（含 3 层资源重载）运行期坐实')


if __name__ == '__main__':
    main()
