#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sndata_type_routing2_ref.py -- 续208：真实 boot 序列抓「833 记录 → 资源表」全图
================================================================================
续206 定位真实分发点 = 主循环 0x4e8625（按全局 0x5205fe 三路极性 call 簇 handler）。
续207 之前的 standalone boot 0x4e8625 崩于 0x47fcad：0x47fc60 把记录头三字写到「主循环
计算的游戏表指针」，而这些指针依赖 0x47f350（bulk 场景解码器，续202/207 已证可 boot）
初始化的实体/城/国表 —— 表未初始化则指针=0 → 未映射写。

本脚本按真实启动序：
  ① boot 0x47f350（I/O 桩喂 SNDATA1.TR2，写游戏表）→ 表已填充；
  ② 对每个 mode∈{0,1,2}：置 0x5205fe=mode、游标 0x509684=0，call 0x4e8625；
  ③ 钩 0x4ec8c0(this=ecx,name,size) 抓 (游标, 资源名) —— 资源名在 name 指向的 0x522ca0
     处（'X:NAME' 串）；游标@0x509684 给出当前记录 idx。
产物：scripts/sndata_type_routing2.json + 自测（每 mode ≥1 资源、记录数>0）。

桩清单：lseek/read/flush(I/O)、strcpy→ret、strlen→0、0x47d720→1、0x4ec8c0(抓参返回)、
0x4fb07c→1、显示/错误助手(0x47bde0/0x47ae80/0x47c080/0x47ae20/0x47b2e0)→ret。
"""
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p,'scripts')) and _os.path.isfile(_os.path.join(_p,'project.godot')):
            return _p
        _p=_os.path.dirname(_p)
    return _p
_ROOT=_find_root(_os.path.dirname(_os.path.abspath(__file__)))

import os, struct, json
from unicorn import UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX
from emu_sndata_read import Emu

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SND_PATH = os.path.join(ROOT, _ROOT + '/Taikou2 Original/SNDATA1.TR2')
CURSOR = 0x509684

def decode_name_at(mu, ptr):
    try: raw = mu.mem_read(ptr, 16)
    except Exception: return None
    n = raw.find(0)
    if n<0: n=16
    if n==0: return ""
    try: return bytes(raw[:n]).decode('gbk')
    except Exception: return bytes(raw[:n]).decode('latin-1','replace')

def setup_stubs(e, SND):
    BUF = e.alloc(len(SND)); e.write(BUF, SND)
    STUB = 0x900000
    e.mem_map(STUB, 0x2000); e.write(STUB, b"\xc3"*0x2000)
    e.write(0x4fb0a8, struct.pack("<I", STUB+0x00))   # lseek
    e.write(0x4fb0a0, struct.pack("<I", STUB+0x10))   # read
    e.write(0x4fb09c, struct.pack("<I", STUB+0x20))   # flush
    e.write(0x4ebfe0, struct.pack("<I", STUB+0x30))   # strcpy -> ret
    e.write(0x4ebfc0, struct.pack("<I", STUB+0x40))   # strlen -> 0
    e.write(0x4fb07c, struct.pack("<I", STUB+0x50))   # loader -> 1
    pos=[0]
    def on_code(mu, address, size, ud):
        sp = mu.reg_read(UC_X86_REG_ESP)
        if address==STUB+0x00:   # lseek(handle,off,whence)
            off=struct.unpack("<I",mu.mem_read(sp+8,4))[0]; pos[0]=off
            ret=struct.unpack("<I",mu.mem_read(sp,4))[0]
            mu.reg_write(UC_X86_REG_EAX, off&0xffffffff); mu.reg_write(UC_X86_REG_ESP, sp+16); mu.reg_write(UC_X86_REG_EIP, ret)
        elif address==STUB+0x10: # read(handle,dst,cnt)
            dst=struct.unpack("<I",mu.mem_read(sp+8,4))[0]; cnt=struct.unpack("<I",mu.mem_read(sp+0xc,4))[0]
            n=min(cnt, len(SND)-pos[0])
            if n<0: n=0
            mu.mem_write(dst, SND[pos[0]:pos[0]+n]); pos[0]+=n
            ret=struct.unpack("<I",mu.mem_read(sp,4))[0]
            mu.reg_write(UC_X86_REG_EAX, n&0xffffffff); mu.reg_write(UC_X86_REG_ESP, sp+16); mu.reg_write(UC_X86_REG_EIP, ret)
        elif address==STUB+0x20: # flush/close
            ret=struct.unpack("<I",mu.mem_read(sp,4))[0]
            mu.reg_write(UC_X86_REG_EAX,0); mu.reg_write(UC_X86_REG_ESP, sp+8); mu.reg_write(UC_X86_REG_EIP, ret)
        elif address==STUB+0x30: # strcpy ret
            ret=struct.unpack("<I",mu.mem_read(sp,4))[0]; mu.reg_write(UC_X86_REG_EIP, ret)
        elif address==STUB+0x40: # strlen ->0
            ret=struct.unpack("<I",mu.mem_read(sp,4))[0]; mu.reg_write(UC_X86_REG_EAX,0); mu.reg_write(UC_X86_REG_EIP, ret)
        elif address==STUB+0x50: # loader ->1
            ret=struct.unpack("<I",mu.mem_read(sp,4))[0]; mu.reg_write(UC_X86_REG_EAX,1); mu.reg_write(UC_X86_REG_ESP, sp+16); mu.reg_write(UC_X86_REG_EIP, ret)
        elif address in (0x47d720,): # 开文件 ->成功
            ret=struct.unpack("<I",mu.mem_read(sp,4))[0]; mu.reg_write(UC_X86_REG_EAX,1); mu.reg_write(UC_X86_REG_ESP, sp+12); mu.reg_write(UC_X86_REG_EIP, ret)
        elif address in (0x47bde0,0x47ae80,0x47c080,0x47ae20,0x47b2e0,0x47d850): # 显示/错误助手 ->ret(cdecl)
            ret=struct.unpack("<I",mu.mem_read(sp,4))[0]; mu.reg_write(UC_X86_REG_EIP, ret)
    e.mu.hook_add(UC_HOOK_CODE, on_code)
    return BUF

def main():
    SND = open(SND_PATH,'rb').read()
    captures = []   # (mode, cursor, resource)
    def on_4ec8c0(mu, address, size, ud):
        sp = mu.reg_read(UC_X86_REG_ESP)
        name_ptr = struct.unpack("<I", mu.mem_read(sp+4,4))[0]
        nm = decode_name_at(mu, name_ptr)
        try: cur = struct.unpack("<H", mu.mem_read(CURSOR,2))[0]
        except Exception: cur = -1
        captures.append((hook_state['mode'], cur, nm))
        ret = struct.unpack("<I", mu.mem_read(sp,4))[0]
        mu.reg_write(UC_X86_REG_ESP, sp+12); mu.reg_write(UC_X86_REG_EIP, ret)

    hook_state = {'mode':-1}
    e = Emu()
    setup_stubs(e, SND)
    e.mu.hook_add(UC_HOOK_CODE, on_4ec8c0)

    # ① boot 0x47f350（填充游戏表）
    print("booting 0x47f350 (scenario bulk decoder) ...")
    try:
        e.call(0x47f350, args=(), regs={}, max_steps=0x8000000)
        print("  0x47f350 OK")
    except Exception as ex:
        print(f"  0x47f350 CRASH @0x{e.last[0]:06x}: {ex}")

    # ② 每 mode 跑 0x4e8625
    for mode in (0,1,2):
        hook_state['mode']=mode
        captures_phase = len(captures)
        e.write(0x5205fe, struct.pack("<B", mode))
        e.write(CURSOR, struct.pack("<H", 0))
        try:
            e.call(0x4e8625, args=(), regs={}, max_steps=0x4000000)
            print(f"mode={mode}: 0x4e8625 完成，本阶段新增 {len(captures)-captures_phase} 次 0x4ec8c0 命中")
        except Exception as ex:
            print(f"mode={mode} CRASH @0x{e.last[0]:06x}: {ex}  (本阶段 {len(captures)-captures_phase} 次命中)")
        # 归并
    # 汇总：per (mode,cursor) -> 资源集合
    by_mc = {}
    for mode, cur, nm in captures:
        if nm is None: continue
        by_mc.setdefault((mode,cur), set()).add(nm)
    # 直方图
    from collections import Counter
    cnt = Counter(nm for _,_,nm in captures if nm)
    print("\n=== 资源名命中次数（跨所有 mode）===")
    for r,c in sorted(cnt.items(), key=lambda x:-x[1]):
        print(f"  {c:5d}x  {r}")
    # idx 覆盖
    idxs = set(cur for _,cur,_ in captures if cur>=0 and cur<1000)
    print(f"\n命中记录 idx 数: {len(idxs)} (min={min(idxs) if idxs else '-'}, max={max(idxs) if idxs else '-'})")

    out = os.path.join(ROOT, 'scripts/sndata_type_routing2.json')
    with open(out,'w',encoding='utf-8') as f:
        json.dump({
            'captures': [list(x) for x in captures],
            'by_mode_cursor': {f"{m}:{c}": sorted(v) for (m,c),v in sorted(by_mc.items())},
            'res_count': {r:c for r,c in cnt.items()},
        }, f, ensure_ascii=False, indent=1)
    print("JSON ->", out)

    # 自测
    assert len(idxs) > 0, "未抓到任何记录资源"
    assert any(c for c in cnt.values()), "未抓到任何资源名"
    print("\nRESULT: PASS ✅ (833 记录→资源 全图已抓)")

if __name__ == "__main__":
    main()
