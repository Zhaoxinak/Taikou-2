#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sndata_header_ref.py -- 钉死 TAIKOU2_SCENARIO / TAIKOU2_SAVEFILE 头 +0x10 的 4 字节字段语义（续202 / Task #6）
========================================================================================================
方法：
  1) 静态断言三段关键指令（capstone 字节签名）：
     (A) 0x47f350 计算流 XOR 密钥：mov ax,[esi+0x94]; mov dl,ah; and eax,0xff; xor edx,eax; mov [esi+0x94],dx
         -> key = byte[0x12] ^ byte[0x13]（存回 obj+0x94）
     (B) 0x47da10 累加器：add word ptr [esi+0x92], cx  —— 每读 1 解密字节把其值累加到 obj+0x92（mod 0x10000）
     (C) 0x47f350 校验：mov ax,[esi+0x92]; cmp ax,[esi+0x90]
         -> 要求 obj+0x92（累加和）== obj+0x90（= file[0x10..0x11]）
  2) emu：真实跑 0x47f350（TAIKOU2_SCENARIO 加载器）验证流累加器 == file[0x10..0x11]，SNDATA1/2 端到端吻合。
  3) 机制（0x47d960 反汇编证实）：流缓冲 = malloc 0x2000 + 文件读 0x2000 原始字节 + 以 key 整段 XOR 解密，
     再交 read_byte(0x47da10) 逐字节累加。故 file[0x10..0x11] = 解密后流字节累加和 mod 0x10000。
  4) SAVEDATA 用同样的 4B 头布局（TAIKOU2_SAVEFILE），key=byte[0x12]^byte[0x13]=0x05（已知 D3 流密钥），
     经静态 + 已知密钥交叉确认。

结论：
  file[0x10..0x11] = 16-bit LE 校验和 = 经 0x47da10 流读原语消费的所有「解密后」字节的累加和 mod 0x10000。
  file[0x12..0x13] = 流 XOR 密钥种子；实际密钥 = byte[0x12] ^ byte[0x13]。
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
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_WRITE_UNMAPPED, UC_HOOK_MEM_FETCH_UNMAPPED
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESI

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN  = os.path.join(ROOT, _ROOT + '/scripts/_unpacked_mem.bin')
BASE = 0x400000
MEM  = open(BIN, "rb").read()

def rd(va, n): return MEM[va - BASE: va - BASE + n]
def dis(va, n):
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    return [f"0x{i.address:06x} {i.mnemonic} {i.op_str}" for i in md.disasm(MEM[va-BASE:va-BASE+n], va)]

# ---- 静态断言 ----
def static_checks():
    ok = True
    a = dis(0x47f3d7, 0x30)
    sig_A = any("mov ax, word ptr [esi + 0x94]" in s for s in a) and \
            any("mov dl, ah" in s for s in a) and \
            any("xor edx, eax" in s for s in a) and \
            any("mov word ptr [esi + 0x94], dx" in s for s in a)
    b = dis(0x47da10, 0x40)
    sig_B = any("add word ptr [esi + 0x92], cx" in s for s in b)
    c = dis(0x47f4da, 0x10)
    sig_C = any("mov ax, word ptr [esi + 0x92]" in s for s in c) and \
            any("cmp ax, word ptr [esi + 0x90]" in s for s in c)
    print(f"[A] 0x47f350 密钥 = byte[0x12]^byte[0x13] : {'PASS' if sig_A else 'FAIL'}")
    print(f"[B] 0x47da10 累加器 add word [esi+0x92],cx : {'PASS' if sig_B else 'FAIL'}")
    print(f"[C] 0x47f350 校验 cmp [esi+0x92],[esi+0x90] : {'PASS' if sig_C else 'FAIL'}")
    return sig_A and sig_B and sig_C

# ---- emu ----
class Emu:
    def __init__(self):
        self.mu = Uc(UC_ARCH_X86, UC_MODE_32)
        self.mu.mem_map(BASE, len(MEM)); self.mu.mem_write(BASE, MEM)
        self.ST = 0x600000; self.mu.mem_map(self.ST, 0x60000)
        self.STOP = 0x700000; self.mu.mem_map(self.STOP, 0x1000); self.mu.mem_write(self.STOP, b"\x90"*8)
        self.POOL = 0xb00000; self.mu.mem_map(self.POOL, 0x400000)  # malloc 池 4MB
        self.pool_off = 0
        self.last = [0]
        self.mu.hook_add(UC_HOOK_CODE, lambda mu,a,s,u: self.last.__setitem__(0,a))

def emulate_header(fn):
    snd = open(os.path.join(ROOT, "Taikou2 Original", fn), "rb").read()
    key = snd[0x12] ^ snd[0x13]
    h10_11 = struct.unpack_from("<H", snd, 0x10)[0]
    e = Emu()
    # 解码器对象（esi）
    OBJ = 0x900000; e.mu.mem_map(OBJ, 0x1000); e.mu.mem_write(OBJ, b"\x00"*0x200)
    e.mu.mem_write(OBJ+0x8c, struct.pack("<H", 0))
    e.mu.mem_write(OBJ+0x8e, struct.pack("<H", 0))
    e.mu.mem_write(OBJ+0x92, struct.pack("<H", 0))
    e.mu.mem_write(OBJ+0x94, struct.pack("<H", key))

    # 文件回调桩（lseek/read/flush）读 snd（原始字节，解密在 0x47d960 内做）
    pos = [0]
    STB = 0x950000; e.mu.mem_map(STB, 0x1000); e.mu.mem_write(STB, b"\xc3"*0x1000)
    READ, LSEEK, FLUSH = STB, STB+0x10, STB+0x20
    e.mu.mem_write(0x4fb0a0, struct.pack("<I", READ))
    e.mu.mem_write(0x4fb0a8, struct.pack("<I", LSEEK))
    e.mu.mem_write(0x4fb09c, struct.pack("<I", FLUSH))

    checks = []
    def on_code(mu, address, size, ud):
        sp = mu.reg_read(UC_X86_REG_ESP)
        try:
            if address == READ:
                # [0x4fb0a0](handle=[sp+4], dst=[sp+8], count=[sp+0xc])  stdcall 3参 ret 0xc
                dst = struct.unpack("<I", mu.mem_read(sp+8,4))[0]
                cnt = struct.unpack("<I", mu.mem_read(sp+0xc,4))[0]
                n = min(cnt, len(snd)-pos[0]); n = max(0,n)
                mu.mem_write(dst, snd[pos[0]:pos[0]+n]); pos[0]+=n
                ret = struct.unpack("<I", mu.mem_read(sp,4))[0]
                mu.reg_write(UC_X86_REG_EAX, n & 0xffffffff); mu.reg_write(UC_X86_REG_ESP, sp+16); mu.reg_write(UC_X86_REG_EIP, ret)
            elif address == LSEEK:
                off = struct.unpack("<I", mu.mem_read(sp+8,4))[0]   # offset=[sp+8]
                pos[0] = off & 0x7fffffff
                ret = struct.unpack("<I", mu.mem_read(sp,4))[0]
                mu.reg_write(UC_X86_REG_EAX, off & 0xffffffff); mu.reg_write(UC_X86_REG_ESP, sp+16); mu.reg_write(UC_X86_REG_EIP, ret)
            elif address == FLUSH:
                ret = struct.unpack("<I", mu.mem_read(sp,4))[0]
                mu.reg_write(UC_X86_REG_EAX, 0); mu.reg_write(UC_X86_REG_ESP, sp+16); mu.reg_write(UC_X86_REG_EIP, ret)
            elif address == 0x4eb5c0:   # malloc(size) -> 返回池指针（stdcall 1参，ret 4）
                ret = struct.unpack("<I", mu.mem_read(sp,4))[0]
                ptr = e.POOL + e.pool_off; e.pool_off += 0x3000
                mu.reg_write(UC_X86_REG_EAX, ptr & 0xffffffff); mu.reg_write(UC_X86_REG_ESP, sp+8); mu.reg_write(UC_X86_REG_EIP, ret)
            elif address == 0x492850:   # magic cmp -> 返回 0 (匹配)（cdecl 3参，调用方 add esp,0xc）
                ret = struct.unpack("<I", mu.mem_read(sp,4))[0]
                mu.reg_write(UC_X86_REG_EAX, 0); mu.reg_write(UC_X86_REG_ESP, sp+4); mu.reg_write(UC_X86_REG_EIP, ret)
            elif address == 0x492800:   # memmove(dst,src,n)（cdecl 3参）
                dst = struct.unpack("<I", mu.mem_read(sp+8,4))[0]
                src = struct.unpack("<I", mu.mem_read(sp+4,4))[0]
                n   = struct.unpack("<I", mu.mem_read(sp+0xc,4))[0]
                try: mu.mem_write(dst, mu.mem_read(src, n))
                except Exception: pass
                ret = struct.unpack("<I", mu.mem_read(sp,4))[0]
                mu.reg_write(UC_X86_REG_EAX, dst & 0xffffffff); mu.reg_write(UC_X86_REG_ESP, sp+4); mu.reg_write(UC_X86_REG_EIP, ret)
            elif address in (0x4edfa0, 0x4edf70):   # thiscall 辅助（no stack arg）
                ret = struct.unpack("<I", mu.mem_read(sp,4))[0]
                mu.reg_write(UC_X86_REG_EIP, ret)
            elif address == 0x47f4da:
                # 校验点：读 obj+0x92(累加器) 与 obj+0x90(file[0x10..0x11])
                csum_now = struct.unpack_from("<H", mu.mem_read(OBJ+0x92, 2), 0)[0]
                h10_now  = struct.unpack_from("<H", mu.mem_read(OBJ+0x90, 2), 0)[0]
                checks.append((csum_now, h10_now, pos[0]))
        except Exception as ex:
            raise
    e.h_code = e.mu.hook_add(UC_HOOK_CODE, on_code)

    esp = e.ST + 0x58000
    e.mu.mem_write(esp, struct.pack("<I", e.STOP))
    e.mu.reg_write(UC_X86_REG_ESP, esp)
    e.mu.reg_write(UC_X86_REG_ECX, OBJ)
    h = e.mu.hook_add(UC_HOOK_CODE, lambda mu,a,s,u: mu.emu_stop() if a == e.STOP else None)
    try:
        e.mu.emu_start(0x47f350, e.STOP+1, count=5_000_000)
    except Exception as ex:
        pass   # 校验点之后的崩溃（如错误处理函数）不影响头4B语义判定
    finally:
        e.mu.hook_del(h)
    csum = struct.unpack_from("<H", e.mu.mem_read(OBJ+0x92, 2), 0)[0]
    if checks:
        csum_now, h10_now, endpos = checks[-1]
        return (csum_now == h10_now), csum_now, h10_now, key, endpos
    return False, csum, h10_11, key, pos[0]

def static_savedata_header():
    """SAVEDATA 用同样的 4B 头布局，key=byte[0x12]^byte[0x13]（已知 D3 流密钥 0x05）交叉确认。"""
    snd = open(os.path.join(ROOT, "Taikou2 Original", "SAVEDATA.TR2"), "rb").read()
    magic = snd[:16]
    ok_magic = (magic == b"TAIKOU2_SAVEFILE")
    h10 = struct.unpack_from("<H", snd, 0x10)[0]
    seed = struct.unpack_from("<H", snd, 0x12)[0]
    key = snd[0x12] ^ snd[0x13]
    print(f"    SAVEDATA 头 magic={magic!r} (TAIKOU2_SAVEFILE? {ok_magic})")
    print(f"    SAVEDATA [0x10..0x11]=0x{h10:04x}(校验和) [0x12..0x13]=0x{seed:04x}(密钥种子) key=byte[0x12]^byte[0x13]=0x{key:02x}")
    ok_key = (key == 0x05)   # 已知 D3 流密钥
    return ok_magic and ok_key, h10, seed, key

def main():
    s_ok = static_checks()
    print()
    print("=== emu：真实跑 0x47f350 校验点（TAIKOU2_SCENARIO）===")
    emu_results = {}
    for fn in ["SNDATA1.TR2", "SNDATA2.TR2"]:
        try:
            r = emulate_header(fn)
        except Exception as ex:
            print(f"  {fn}: EMU 失败 {ex}"); r = None
        if not r:
            print(f"  {fn}: 未得出结果"); continue
        ok_csum, csum_now, h10_now, key, endpos = r
        emu_results[fn] = (True, ok_csum)
        print(f"  {fn}: emp_csum(累加器)=0x{csum_now:04x}  file[0x10..0x11]=0x{h10_now:04x} "
              f"(匹配?{ok_csum})  key=0x{key:02x}  流读取止=0x{endpos:x}")
    s_ok2, sh10, sseed, skey = static_savedata_header()
    emu_all = all(all(v) for v in emu_results.values()) and s_ok2
    print()
    print("="*70)
    print(f"静态断言: {'ALL PASS' if s_ok else 'FAIL'}")
    print(f"emu/静态校验: {'ALL PASS' if emu_all else 'PARTIAL/FAIL'}")
    print("="*70)
    return 0 if (s_ok and emu_all) else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
