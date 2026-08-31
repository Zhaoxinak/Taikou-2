# -*- coding: utf-8 -*-
# entity_tail_ref.py — 武将实体表(0x519868, stride 47) 尾部状态字段解码 (续122)
#
# 证据（全部来自 2MB 脱壳映像 _unpacked_mem.bin，VA=off+0x400000）：
#  · +0x29: 写入器 0x49a7bf  `mov eax,[esp+4]; cmp ax,0x64; jbe; mov eax,0x64;
#                             mov [ecx+0x29],al; ret4`  -> 值被钳制到 [0,100]。
#         消费方按 40/50/95/100 分档（0x4438ba cmp 0x28/0x5f, 0x45a384 cmp 0x32, 0x4aa72d cmp 0x64）
#         => 高度疑似 **忠诚 loyalty (0..100)**。
#  · +0x2c: 16-bit 状态字；+0x2d 是其**高字节**，由以下 setter 显式打包（续122 实测）：
#     0x49a7e0: and word,0xf8ff ; or word,(arg<<8)        -> 整个 +0x2d 字节 = 值(0..255)，游戏用其低3位为 code
#     0x49a808: or  [+0x2d],8    (位11 of word = +0x2d.3)  flag
#     0x49a828: or  [+0x2d],0x10 (位12 of word = +0x2d.4)  flag
#     0x49a840: and word,0x9fff ; shl eax,0xd ; or         -> 位13,14 (+0x2d.5,.6) = 2-bit 字段(0..3)
#     0x49a868: or  [+0x2d],0x80 (位15 of word = +0x2d.7)  = 已故/除籍
#     消费方：test [+0x2d],7 读取低3位 code（0x447843 范围比较 / 0x4d3f07 精确匹配）；
#             test [+0x2d],8 / 0x10 / 0x80 读取各 flag；test [+0x2d],0x60 读取 2-bit 字段。
#  · +0x2e: 1-byte 状态，0x49a880/0x49a8a0 `or [+0x2e],1/2`；test [+0x2e],4 @0x419d93。
#
# 注：0x49bcxx 簇（dword@+0x28，word@+0x2a/@+0x2c 镜像打包）属**另一 struct**（实体无 +0x28 dword），
#     其 +0x29 flag/3-bit 写入不作用到实体忠诚字节，故不构成矛盾。
import sys

STRIDE = 47
LOYALTY_MAX = 100

# +0x2d 字节内的位域（高字节 of +0x2c word）
MASK_RANK3   = 0x07   # 低3位: 3-bit 类别/身分码 (0..7)
BIT_F3       = 0x08   # 位3: flag
BIT_F4       = 0x10   # 位4: flag
MASK_F2B     = 0x60   # 位5-6: 2-bit 字段 (0..3)
BIT_DEAD     = 0x80   # 位7: 已故/除籍

# +0x2c 16-bit 状态字内这些位对应 +0x2d 字节（即 位8..15）
W_RANK3  = 0x0700   # 低3位 code 占 位8-10
W_F3     = 0x0800   # 位11
W_F4     = 0x1000   # 位12
W_F2B    = 0x6000   # 位13-14
W_DEAD   = 0x8000   # 位15


def set_loyalty(v):
    """0x49a7bf: 钳制到 [0,100]。"""
    return max(0, min(v, LOYALTY_MAX)) & 0xff


def get_rank3(word):
    """+0x2d 低3位 = 3-bit 身分/类别码。"""
    return (word >> 8) & MASK_RANK3


def set_rank3(word, v):
    """0x49a7e0: 整个 +0x2d 字节写入 v(0..255)，低3位为 code。"""
    return (word & 0xF8FF) | ((v & 0xFF) << 8)


def is_dead(word):
    return bool(word & W_DEAD)


def set_dead(word, on=True):
    return word | W_DEAD if on else word & ~W_DEAD & 0xFFFF


def get_f3(word):
    return bool(word & W_F3)


def set_f3(word, on=True):
    return word | W_F3 if on else word & ~W_F3 & 0xFFFF


def get_f4(word):
    return bool(word & W_F4)


def set_f4(word, on=True):
    return word | W_F4 if on else word & ~W_F4 & 0xFFFF


def get_field2b(word):
    """+0x2d.5-.6 = 2-bit 字段 (0..3)。"""
    return (word & W_F2B) >> 13


def set_field2b(word, v):
    """0x49a840: and 0x9fff ; shl v,0xd ; or。"""
    return (word & 0x9FFF) | ((v & 0x3) << 13)


def _run_tests():
    ok = 0; tot = 0
    def chk(name, cond):
        nonlocal ok, tot
        tot += 1
        if cond: ok += 1
        else: print(f"  FAIL: {name}")
    # 忠诚钳制
    chk("loyalty clamp 150->100", set_loyalty(150) == 100)
    chk("loyalty clamp -5->0", set_loyalty(-5) == 0)
    chk("loyalty pass 73", set_loyalty(73) == 73)
    # 3-bit code
    chk("rank3 of 0x0500 == 5", get_rank3(0x0500) == 5)
    w = set_rank3(0x0000, 5); chk("set_rank3 5 -> 0x0500", w == 0x0500)
    w = set_rank3(0x00AB, 7); chk("set_rank3 keeps low byte", (w >> 8) == 7 and (w & 0xFF) == 0xAB)
    w = set_rank3(0x1234, 7); chk("set_rank3 hi low3==7, low byte kept", ((w >> 8) & 7) == 7 and (w & 0xFF) == 0x34)
    # dead flag
    chk("dead set", is_dead(set_dead(0x0000)))
    chk("dead clear", not is_dead(set_dead(0x8000, False)))
    # f3 / f4
    chk("f3 set->bit11", get_f3(set_f3(0)) and (set_f3(0) & W_F3))
    chk("f4 set->bit12", get_f4(set_f4(0)) and (set_f4(0) & W_F4))
    # 2-bit field
    chk("field2b of 0x6000 == 3", get_field2b(0x6000) == 3)
    w = set_field2b(0x0000, 2); chk("set_field2b 2 -> 0x4000", w == 0x4000)
    w = set_field2b(0xFFFF, 1); chk("set_field2b clears 13-14 then sets", get_field2b(w) == 1)
    # 组合：一个典型实体状态字：code=3, f3=1, 2bit=2, dead=0
    w = 0
    w = set_rank3(w, 3)
    w = set_f3(w)
    w = set_field2b(w, 2)
    chk("combo rank3==3", get_rank3(w) == 3)
    chk("combo f3 on", get_f3(w))
    chk("combo 2bit==2", get_field2b(w) == 2)
    chk("combo not dead", not is_dead(w))
    # +0x2d 字节分解一致
    hi = (w >> 8) & 0xFF
    chk("hi byte low3 == 3", hi & MASK_RANK3 == 3)
    chk("hi byte bit3 set", hi & BIT_F3)
    chk("hi byte 0x60 field == 2", (hi & MASK_F2B) >> 5 == 2)
    chk("hi byte bit7 clear", not (hi & BIT_DEAD))
    print(f"RESULT: {ok}/{tot} checks passed")
    return ok == tot


if __name__ == '__main__':
    sys.exit(0 if _run_tests() else 1)
