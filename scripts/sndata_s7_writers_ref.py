#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sndata_s7_writers_ref.py -- 续207：emu 抓 S7 每城表 0x516a28 写入者（收口 续192 残留敞口 +0x04/+0x0c）
====================================================================================================
续192 钉死 S7 结构 + +0x0f 专属位域，但 +0x04(指针链)/+0x0c(3-bit 标志) 写入路径未知，
「须 emu 钩 0x516a28 抓读者/写者」。本脚本复用续202 已证 boot 的 0x47f350（TAIKOU2_SCENARIO
bulk 解码器，18 子解码器 S0..S17 写实体/城/国/S15/S6/S17 等），在其运行期挂 UC_HOOK_MEM_WRITE
于 S7 区 0x516a28..0x516a28+0x1400(200×16B)，抓所有写 S7 的指令(EIP) + 写偏移 + 值。

若 0x47f350 写 S7 → 直接得写入者（收口）；若不写 → 负向结论（S7 在运行期其它相位填充，
非剧本 bulk 解码），指导下一步 boot 目标。
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

import os, struct
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX, UC_X86_REG_ECX

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN  = os.path.join(ROOT, _ROOT + '/scripts/_unpacked_mem.bin')
MEM  = open(BIN, "rb").read()
BASE = 0x400000
S7_BASE = 0x516a28
S7_END  = S7_BASE + 200 * 16

def main():
    snd = open(os.path.join(ROOT, _ROOT + '/Taikou2 Original/SNDATA1.TR2'), "rb").read()
    key = snd[0x12] ^ snd[0x13]
    mu = Uc(UC_ARCH_X86, UC_MODE_32)
    mu.mem_map(BASE, len(MEM)); mu.mem_write(BASE, MEM)
    ST = 0x600000; mu.mem_map(ST, 0x60000)
    STOP = 0x700000; mu.mem_map(STOP, 0x1000); mu.mem_write(STOP, b"\x90"*8)
    POOL = 0xb00000; mu.mem_map(POOL, 0x400000)
    OBJ = 0x900000; mu.mem_map(OBJ, 0x1000); mu.mem_write(OBJ, b"\x00"*0x200)
    mu.mem_write(OBJ+0x92, struct.pack("<H", 0)); mu.mem_write(OBJ+0x94, struct.pack("<H", key))
    pos = [0]
    STB = 0x950000; mu.mem_map(STB, 0x1000); mu.mem_write(STB, b"\xc3"*0x1000)
    READ, LSEEK, FLUSH = STB, STB+0x10, STB+0x20
    mu.mem_write(0x4fb0a0, struct.pack("<I", READ))
    mu.mem_write(0x4fb0a8, struct.pack("<I", LSEEK))
    mu.mem_write(0x4fb09c, struct.pack("<I", FLUSH))
    pool_off = [0]
    writes = []
    def on_code(mu, address, size, ud):
        sp = mu.reg_read(UC_X86_REG_ESP)
        try:
            if address == READ:
                dst = struct.unpack("<I", mu.mem_read(sp+8,4))[0]
                cnt = struct.unpack("<I", mu.mem_read(sp+0xc,4))[0]
                n = min(cnt, len(snd)-pos[0]); n = max(0,n)
                mu.mem_write(dst, snd[pos[0]:pos[0]+n]); pos[0]+=n
                ret = struct.unpack("<I", mu.mem_read(sp,4))[0]
                mu.reg_write(UC_X86_REG_EAX, n); mu.reg_write(UC_X86_REG_ESP, sp+16); mu.reg_write(UC_X86_REG_EIP, ret)
            elif address == LSEEK:
                off = struct.unpack("<I", mu.mem_read(sp+8,4))[0]
                pos[0] = off & 0x7fffffff
                ret = struct.unpack("<I", mu.mem_read(sp,4))[0]
                mu.reg_write(UC_X86_REG_EAX, off); mu.reg_write(UC_X86_REG_ESP, sp+16); mu.reg_write(UC_X86_REG_EIP, ret)
            elif address == FLUSH:
                ret = struct.unpack("<I", mu.mem_read(sp,4))[0]
                mu.reg_write(UC_X86_REG_EAX, 0); mu.reg_write(UC_X86_REG_ESP, sp+16); mu.reg_write(UC_X86_REG_EIP, ret)
            elif address == 0x4eb5c0:   # malloc
                ret = struct.unpack("<I", mu.mem_read(sp,4))[0]
                ptr = POOL + pool_off[0]; pool_off[0] += 0x3000
                mu.reg_write(UC_X86_REG_EAX, ptr); mu.reg_write(UC_X86_REG_ESP, sp+8); mu.reg_write(UC_X86_REG_EIP, ret)
            elif address == 0x492850:   # magic cmp -> 0
                ret = struct.unpack("<I", mu.mem_read(sp,4))[0]
                mu.reg_write(UC_X86_REG_EAX, 0); mu.reg_write(UC_X86_REG_ESP, sp+4); mu.reg_write(UC_X86_REG_EIP, ret)
            elif address == 0x492800:   # memmove
                dst = struct.unpack("<I", mu.mem_read(sp+8,4))[0]
                src = struct.unpack("<I", mu.mem_read(sp+4,4))[0]
                n   = struct.unpack("<I", mu.mem_read(sp+0xc,4))[0]
                try: mu.mem_write(dst, mu.mem_read(src, n))
                except Exception: pass
                ret = struct.unpack("<I", mu.mem_read(sp,4))[0]
                mu.reg_write(UC_X86_REG_EAX, dst); mu.reg_write(UC_X86_REG_ESP, sp+4); mu.reg_write(UC_X86_REG_EIP, ret)
            elif address in (0x4edfa0, 0x4edf70):
                ret = struct.unpack("<I", mu.mem_read(sp,4))[0]
                mu.reg_write(UC_X86_REG_EIP, ret)
        except Exception:
            pass
    mu.hook_add(UC_HOOK_CODE, on_code)
    def on_write(mu, access, address, size, value, ud):
        if S7_BASE <= address < S7_END:
            eip = mu.reg_read(UC_X86_REG_EIP)
            writes.append((eip, address - S7_BASE, size, value & ((1<<(8*size))-1)))
    mu.hook_add(UC_HOOK_MEM_WRITE, on_write)

    esp = ST + 0x58000
    mu.mem_write(esp, struct.pack("<I", STOP))
    mu.reg_write(UC_X86_REG_ESP, esp)
    mu.reg_write(UC_X86_REG_ECX, OBJ)
    h = mu.hook_add(UC_HOOK_CODE, lambda mu,a,s,u: mu.emu_stop() if a == STOP else None)
    try:
        mu.emu_start(0x47f350, STOP+1, count=8_000_000)
    except Exception as ex:
        print(f"(emu 在 0x{mu.reg_read(UC_X86_REG_EIP):06x} 异常: {ex} — 忽略，取已捕获写)")
    finally:
        mu.hook_del(h)

    print(f"=== S7 区 0x{S7_BASE:06x}..0x{S7_END:06x} 写入捕获（0x47f350 运行期）===")
    print(f"写次数: {len(writes)}")
    if writes:
        # 按 EIP 归并，统计写偏移分布
        from collections import Counter, defaultdict
        by_eip = defaultdict(list)
        for eip, off, sz, val in writes:
            by_eip[eip].append((off, sz, val))
        for eip in sorted(by_eip):
            recs = by_eip[eip]
            offs = sorted(set(o for o,s,v in recs))
            print(f"  0x{eip:06x}: {len(recs)} 次, 写偏移={offs[:24]}{'...' if len(offs)>24 else ''}")
        # 特定相对偏移 +0x04 / +0x0c 写入者（按 16B 条目取模）
        for target in (0x04, 0x0c):
            hit = [(hex(eip), sz, val) for eip,off,sz,val in writes if off % 16 == target]
            print(f"  >> S7+0x{target:02x} 写入者: {len(hit)} 次 -> {hit[:6]}")
    else:
        print("  ** 0 次写入 S7 —— 负向结论：S7 不在剧本 bulk 解码(0x47f350)期填充，**")
        print("     而是在运行期其它相位（城/评定/内政处理）填充，须 boot 对应子系统抓写者。")
    with open(os.path.join(ROOT, _ROOT + '/scripts/sndata_s7_writers.json'), "w", encoding="utf-8") as f:
        import json
        json.dump({'writes': [list(w) for w in writes]}, f, indent=1)
    print("RESULT:", "writers_found" if writes else "no_s7_write_in_47f350")

if __name__ == "__main__":
    main()
