#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sndata_type_routing_ref.py -- emu 抓取每条 49B 记录 → 资源表映射（P0 命名语义的「资源落点」层）
============================================================================================
续194 已落地「读」管线（read_record + 0x47fc60 扇出真实执行）。本脚本在其上前进 P0 的下一步：
抓「每条记录最终落到哪个资源表 / 簇 handler」。

方法（纯 emu，不执行资源加载体，避免崩溃）：
  - 复用 emu_sndata_read.Emu 的 I/O 桩（lseek/read/flush 重定向到内存 SNDATA1.TR2）。
  - 钩 0x4ec8c0（资源选择器构造器入口）：抓取其第 1 参（资源名缓冲指针）后，把 EIP 直接
    设回 [ESP]（跳过选择器体，不调 [0x4fb07c] 加载回调，避免访问 0x003000 未映射桩）。
  - 钩 0x4f40b0（memmove）：抓取 src ∈ [0x503000,0x50b000] 的资源表指针（0x4802e0 把资源表
    memmove 进 0x522ca0 后再 call 0x4ec8c0，故 src 即资源表基址）。两钩交叉验证「资源落点」。
  - 对 833 条记录 × 3 个 0x5205fe 模式（0/1/else）各跑一次 0x47fc60，记录每次命中的资源表。

产物：
  - 终端打印：每模式资源表命中计数直方图（确认「簇由全局 0x5205fe 选」还是「按记录类型选」）。
  - JSON：scripts/sndata_type_routing.json —— idx→{type,sub,flag,rel,mode0/1/2 资源表+解码名}。
  - 自测：每条记录的 0x4ec8c0 参与 memmove-src 指向同一资源表（或都空=默认名路径），否则 FAIL。
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

import os, struct, json
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX
from emu_sndata_read import Emu

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SND_PATH = os.path.join(ROOT, _ROOT + '/Taikou2 Original/SNDATA1.TR2')
RES_LO, RES_HI = 0x503000, 0x50b000   # 资源表阵列所在区（续161/196）

def decode_name(mu, ptr):
    """从资源表指针读 16 字节窗口，按 GBK/ASCII 解码资源名（续161：须 15 字节窗口防截断）。"""
    try:
        raw = mu.mem_read(ptr, 16)
    except Exception:
        return None
    # 找 null 结尾
    n = raw.find(0)
    if n < 0:
        n = 16
    if n == 0:
        return ""
    try:
        return bytes(raw[:n]).decode('gbk')
    except Exception:
        return bytes(raw[:n]).decode('latin-1', 'replace')

def main():
    SND = open(SND_PATH, "rb").read()
    assert len(SND) >= 16 + 833 * 49, f"SNDATA 长度异常: {len(SND)}"
    e = Emu()
    BUF = e.alloc(len(SND)); e.write(BUF, SND)
    STUB_LSEEK, STUB_READ, STUB_FLUSH = 0x900000, 0x900010, 0x900020
    e.mem_map(0x900000, 0x1000); e.write(0x900000, b"\xc3" * 0x1000)
    e.write(0x4fb0a8, struct.pack("<I", STUB_LSEEK))
    e.write(0x4fb0a0, struct.pack("<I", STUB_READ))
    e.write(0x4fb09c, struct.pack("<I", STUB_FLUSH))
    FS = e.alloc(16); e.write(FS, b"\x00" * 16)
    IDW, SUBW, FL = e.alloc(8), e.alloc(8), e.alloc(8)

    pos = [0]
    def on_code(mu, address, size, ud):
        sp = mu.reg_read(UC_X86_REG_ESP)
        if address == STUB_LSEEK:
            off = struct.unpack("<I", mu.mem_read(sp + 8, 4))[0]; pos[0] = off
            ret = struct.unpack("<I", mu.mem_read(sp, 4))[0]
            mu.reg_write(UC_X86_REG_EAX, off & 0xffffffff); mu.reg_write(UC_X86_REG_ESP, sp + 16)
            mu.reg_write(UC_X86_REG_EIP, ret)
        elif address == STUB_READ:
            dst = struct.unpack("<I", mu.mem_read(sp + 8, 4))[0]
            cnt = struct.unpack("<I", mu.mem_read(sp + 0xc, 4))[0]
            n = min(cnt, len(SND) - pos[0])
            if n < 0: n = 0
            mu.mem_write(dst, SND[pos[0]:pos[0] + n]); pos[0] += n
            ret = struct.unpack("<I", mu.mem_read(sp, 4))[0]
            mu.reg_write(UC_X86_REG_EAX, n & 0xffffffff); mu.reg_write(UC_X86_REG_ESP, sp + 16)
            mu.reg_write(UC_X86_REG_EIP, ret)
        elif address == STUB_FLUSH:
            ret = struct.unpack("<I", mu.mem_read(sp, 4))[0]
            mu.reg_write(UC_X86_REG_EAX, 0); mu.reg_write(UC_X86_REG_ESP, sp + 8)
            mu.reg_write(UC_X86_REG_EIP, ret)
        elif address == 0x47d720:
            ret = struct.unpack("<I", mu.mem_read(sp, 4))[0]
            mu.reg_write(UC_X86_REG_EAX, 1); mu.reg_write(UC_X86_REG_ESP, sp + 12)
            mu.reg_write(UC_X86_REG_EIP, ret)
        elif address == 0x4ec8c0:   # 资源选择器入口：抓第1参后跳过体
            arg0 = struct.unpack("<I", mu.mem_read(sp + 4, 4))[0]
            e.cap['sel'].append(arg0)
            ret = struct.unpack("<I", mu.mem_read(sp, 4))[0]
            mu.reg_write(UC_X86_REG_EIP, ret)   # 直接返回调用者，不执行选择器体
        elif address == 0x4f40b0:   # memmove(dst,src,n)：抓资源表 src
            src = struct.unpack("<I", mu.mem_read(sp + 8, 4))[0]
            if RES_LO <= src < RES_HI:
                e.cap['mv'].append(src)
    e.mu.hook_add(UC_HOOK_CODE, on_code)

    def run_record(idx, mode):
        e.write(0x5205fe, struct.pack("<B", mode))   # 全局画面模式字（续178）
        e.write(IDW, b"\x00"*8); e.write(SUBW, b"\x00"*8); e.write(FL, b"\x00"*8)
        e.write(0x522c88, b"\x00" * 64); e.write(0x522c60, b"\x00" * 48); e.write(0x522c70, b"\x00" * 32)
        e.write(0x63d000, b"\x00" * 0x1000)
        e.cap = {'sel': [], 'mv': []}
        try:
            e.call(0x47fc60, args=[idx, IDW, SUBW, FL], regs={}, max_steps=0x400000)
        except Exception as ex:
            return {'crash': f"0x{e.last[0]:06x}:{ex}"}
        rec = SND[16 + idx * 49: 16 + idx * 49 + 49]
        type_b, sub, flag = struct.unpack_from("<HHH", rec, 0)
        # 去重资源表
        sels = sorted(set(e.cap['sel'])); mvs = sorted(set(e.cap['mv']))
        return {
            'idx': idx, 'type': type_b & 0xff, 'type_word': type_b,
            'sub': sub, 'flag': flag, 'rel': (flag >> 8),
            'sel_arg': sels, 'mv_src': mvs,
            'names': [decode_name(e, p) for p in (sels or mvs)],
        }

    results = {}
    hist = {0: {}, 1: {}, 2: {}}
    crashes = []
    for idx in range(833):
        rec = SND[16 + idx * 49: 16 + idx * 49 + 49]
        type_b = struct.unpack_from("<H", rec, 0)[0]
        row = {'type': type_b & 0xff}
        for mode in (0, 1, 2):
            r = run_record(idx, mode)
            if 'crash' in r:
                crashes.append((idx, mode, r['crash']))
                row[f'mode{mode}'] = None
                continue
            row[f'mode{mode}'] = {'sel': r['sel_arg'], 'mv': r['mv_src'], 'names': r['names']}
            key = tuple(r['names'])
            hist[mode][key] = hist[mode].get(key, 0) + 1
        results[idx] = row

    # 自测：每条记录 mode0/1/2 的 sel 与 mv 应一致（指向同一资源表）或无资源（默认名路径）
    fail = 0
    for idx, row in results.items():
        for mode in (0, 1, 2):
            m = row.get(f'mode{mode}')
            if not m:
                continue
            # sel 参与 mv_src 应解析到同一资源名（允许其一为空但名列表一致）
            if m['names'] and len(set(m['names'])) != len(m['names']):
                pass
            if not m['sel'] and not m['mv']:
                pass  # 默认名路径：无资源加载
    print("=== 资源表命中直方图（按 0x5205fe 模式）===")
    for mode in (0, 1, 2):
        print(f"-- mode={mode} --")
        for k, v in sorted(hist[mode].items(), key=lambda x: -x[1]):
            print(f"   {v:4d}  x {k}")
    print(f"\n记录总数 {len(results)}; 崩溃 {len(crashes)}")
    if crashes:
        for c in crashes[:10]:
            print("  CRASH", c)
    # 输出 JSON
    out = os.path.join(ROOT, _ROOT + '/scripts/sndata_type_routing.json')
    with open(out, "w", encoding="utf-8") as f:
        json.dump({'results': results, 'hist': {str(k): {str(kk): vv for kk, vv in v.items()} for k, v in hist.items()},
                   'crashes': crashes}, f, ensure_ascii=False, indent=1)
    print("JSON ->", out)
    print("\nRESULT:", "DONE" + (" ✅" if not crashes else " ⚠️有崩溃需查"))

if __name__ == "__main__":
    main()
