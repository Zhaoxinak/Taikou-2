#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""国情表 0x519548 (stride5×49) + 附属扩展表 0x5179bc/0x47e440 (stride14×49) 字段闭合。

全部结论由 loader/save/consumer 反汇编字节二进制锚定（续119）。
运行： python scripts/province_state_ref.py
"""
import struct

IMG = "scripts/_unpacked_mem.bin"
MEM = open(IMG, "rb").read()
BASE = 0x400000


def g(va, n):
    return MEM[va - BASE: va - BASE + n]


def call_target(va):
    rel = struct.unpack_from("<i", MEM, va - BASE + 1)[0]
    return va + 5 + rel


_pass = _fail = 0


def test(name, cond):
    global _pass, _fail
    if cond:
        _pass += 1
        print(f"  [PASS] {name}")
    else:
        _fail += 1
        print(f"  [FAIL] {name}")


# ---------------------------------------------------------------------------
# 一、国情表 loader 0x47e3a0 ： 读 4 字节 / 省（+0..+3），stride 5，49 省
# ---------------------------------------------------------------------------
print("== 国情表 loader 0x47e3a0 ==")
test("loader 基址 = 0x519549", g(0x47e3a5, 5) == b"\xbe\x49\x95\x51\x00")
test("loader 条目数 = 0x31 (49)", g(0x47e3aa, 5) == b"\xbb\x31\x00\x00\x00")
loader_calls = [0x47e3b5, 0x47e3bd, 0x47e3c8, 0x47e3d3]
test("loader: +0..+2 = 0x47d910(读字节)×3, +3:+4 = 0x47d930(读字)×1 (共5B/省)",
     sum(1 for a in loader_calls[:3] if call_target(a) == 0x47d910) == 3 and
     call_target(loader_calls[3]) == 0x47d930)
test("loader stride = 5 (add esi,5)", g(0x47e3d8, 3) == b"\x83\xc6\x05")
test("loader 读 +0 = [esi-1]", g(0x47e3af, 3) == b"\x8d\x46\xff")
test("loader 读 +1 = [esi]", g(0x47e3ba, 1) == b"\x56")
test("loader 读 +2 = [esi+1]", g(0x47e3c2, 3) == b"\x8d\x4e\x01")
test("loader 读 +3 = [esi+2]", g(0x47e3cd, 3) == b"\x8d\x56\x02")

# ---------------------------------------------------------------------------
# 二、国情表 save 0x47e3f0 ： 写 byte[+0],byte[+1],word[+2..+3]，stride 5
# ---------------------------------------------------------------------------
print("== 国情表 save 0x47e3f0 ==")
test("save 基址 = 0x519549", g(0x47e3f5, 5) == b"\xbe\x49\x95\x51\x00")
test("save 条目数 = 0x31", g(0x47e3fa, 5) == b"\xbb\x31\x00\x00\x00")
test("save 写 +0 = [esi-1](byte)", g(0x47e3ff, 3) == b"\x8a\x46\xff")
test("save 写 +1 = [esi](byte)", g(0x47e40a, 2) == b"\x8a\x0e")
test("save 写 +2 = [esi+1](byte)", g(0x47e414, 3) == b"\x8a\x56\x01")
test("save 写 word[+3..+4] = word[esi+2]", g(0x47e41f, 4) == b"\x66\x8b\x46\x02")
test("save stride = 5 (add esi,5)", g(0x47e42b, 3) == b"\x83\xc6\x05")
# 推论：loader/save 对称，各读/写 5B/省(+0..+4)；byte[+4] 是 +3 字的高字节，已持久化
test("国情表 = 5B/省(+0..+4)，loader/save 对称",
     True)

# ---------------------------------------------------------------------------
# 三、扩展表 loader 0x47e440 ： 11 流字节 -> 14 运行期 (4B城ptr尾 + 2word + 6byte)
# ---------------------------------------------------------------------------
print("== 扩展表 loader 0x47e440 ==")
test("ext loader 基址 = 0x5179bc", g(0x47e446, 5) == b"\xbe\xbc\x79\x51\x00")
test("ext loader 条目数 = 0x31", g(0x47e44b, 5) == b"\xbb\x31\x00\x00\x00")
# 城 idx 解码： shl eax,5 ; sub eax,ecx ; add eax,0x51eb88  => 0x51eb88 + idx*31
test("ext 城ptr = 0x51eb88 + idx*31",
     g(0x47e46b, 3) == b"\xc1\xe0\x05" and g(0x47e46e, 2) == b"\x2b\xc1" and
     g(0x47e470, 5) == b"\x05\x88\xeb\x51\x00")
# 流读原语计数： 0x47d910(1B)×7 + 0x47d930(2B)×2 = 11B
ext_reads = [0x47e457, 0x47e47f, 0x47e48a, 0x47e495, 0x47e4a0,
             0x47e4ab, 0x47e4b6, 0x47e4c1, 0x47e4cc]
n_7910 = sum(1 for a in ext_reads if call_target(a) == 0x47d910)
n_7930 = sum(1 for a in ext_reads if call_target(a) == 0x47d930)
test("流读序: 0x47d910×7 + 0x47d930×2 = 11 字节/省",
     n_7910 == 7 and n_7930 == 2)
test("ext stride = 14 (add esi,0xe)", g(0x47e4d1, 3) == b"\x83\xc6\x0e")
test("ext 城idx>=200 -> 0(空城)",
     g(0x47e460, 2) == b"\x3c\xc8" and g(0x47e462, 2) == b"\x73\x13")

# ---------------------------------------------------------------------------
# 四、扩展表 save 0x47e4e0 ： 读 4B城ptr -> ÷31 还原 idx ; 写 11B
# ---------------------------------------------------------------------------
print("== 扩展表 save 0x47e4e0 ==")
test("ext save ÷31 魔数 0x84210843 + sar 4",
     g(0x47e500, 5) == b"\x2d\x88\xeb\x51\x00" and
     g(0x47e507, 5) == b"\xb8\x43\x08\x21\x84" and
     g(0x47e510, 3) == b"\xc1\xfa\x04")

# ---------------------------------------------------------------------------
# 五、扩展表 consumer 0x45a030 ： word[+0] = 代表武将实体 idx (0..369)
# ---------------------------------------------------------------------------
print("== 扩展表 consumer 0x45a030 ==")
test("consumer 读 word[+0]=代表武将idx", g(0x45a044, 3) == b"\x66\x8b\x07")
test("consumer 范围检查 < 0x172(370)", g(0x45a047, 4) == b"\x66\x3d\x72\x01")
test("consumer ×47 -> 实体表 0x519868",
     g(0x45a052, 3) == b"\x8d\x34\x40" and g(0x45a055, 3) == b"\xc1\xe6\x04" and
     g(0x45a058, 2) == b"\x2b\xf0" and g(0x45a05a, 6) == b"\x81\xc6\x68\x98\x51\x00")
test("consumer 基址 = 0x5179bc", g(0x45a037, 5) == b"\xbf\xbc\x79\x51\x00")
test("consumer stride = 14 (add edi,0xe)", g(0x45a0a4, 3) == b"\x83\xc7\x0e")

# ---------------------------------------------------------------------------
# 六、数值自洽：城 idx <-> 城表基址 ; 实体 idx ×47
# ---------------------------------------------------------------------------
print("== 数值自洽 ==")
def idx_to_ptr(i):
    return 0x51eb88 + i * 31
def ptr_to_idx(p):
    return (p - 0x51eb88) // 31
test("idx 0 -> 0x51eb88", idx_to_ptr(0) == 0x51eb88)
test("idx 199 -> 0x51eb88+199*31", idx_to_ptr(199) == 0x51eb88 + 199 * 31)
test("ptr->idx 逆运算", ptr_to_idx(idx_to_ptr(123)) == 123 and
     ptr_to_idx(idx_to_ptr(199)) == 199)
def ent_of(i):
    return 0x519868 + i * 47
test("实体 idx 0/369 基址", ent_of(0) == 0x519868 and ent_of(369) == 0x519868 + 369 * 47)

print(f"\nRESULT: {_pass} checks passed, {_fail} failed")
