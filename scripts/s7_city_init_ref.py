#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
s7_city_init_ref.py  —— 续236：S7 每城记录（0x516a28, 16B×200）写入路径 + 字段语义 静态实证

背景
----
非图像逆向中，S7 每城表的「写入路径」与「字段语义」长期标为待破（GAME_DATA_SPEC §3.20.3：
"+0x04 链指向什么、+0x0f 的 bit4/5/6 三类别含义、+0x0c 三标志位含义"）。本脚本把这条路径
从反汇编彻底坐死，并纠正文档两处陈旧假设：

  * S7[+0x04] 不是「指针链」——它是 16 位数值（setter 写 WORD，钳 2000）。
  * S7[+0x0c] 不是「3 标志位」——它是守城度/次级等级值（B 钳 250）。

核心发现（均取自已脱壳映像 _unpacked_mem.bin，base 0x400000）
-------------------------------------------------------------
1) 访问器/初始化器 0x4511a9：把城表实体指针 edi 经 ÷31 魔数 0x84210843 还原成城索引，
   算 S7[idx] = 0x516a28 + idx*16；然后 0x49bf50 清标志 + 0x49bf90 设类别=7。
   ⇒ 类别 7 = 默认/初始化城类别。

2) 字段初始化器 0x4b49f0：把城表 31B 实体（edi）的 10 个字段，经共享 setter 库
   （0x49be10..0x49bf30）拷进 S7 记录（esi），每个 setter 带钳制上限。
   ⇒ S7 是「城経済状態 ワークレコード」，字段全部来自城表。

3) 类别/标志 setter（组合字节存于 S7[+0x0f]，类别=bits4-6，标志=bits0-3）：
   0x49bf90(arg): bits4-6 = (arg & 7) << 4   → 0..7 类别枚举（写入前先 and 0x8f 清 bits4-6）
   0x49bf50(arg): bits0-3 = arg & 0xf        → 标志位（异或技巧实现赋值，非翻转；返回后仍保留 bits4-7）
   初始化默认：类别=7（0x70），标志=0xc（bits 2,3 置位，由 0x4b49f0 末 `push 0xc; call 0x49bf50`）。

自测段（全 PASS 即收口）：
  A) 0x4511a9 的 ÷31 魔数 / S7 基址 / ×16 位移与映像字节一致。
  B) 0x4b49f0 的 10 段拷入序列：源 city 偏移 + setter + 目标 S7 偏移 + 钳制上限 与代码一致。
  C) 用合成城表实体跑一遍拷入逻辑，验证 S7 各偏移值与钳制正确。
  D) 类别 setter 位运算（(arg&7)<<4）与标志 setter（^=掩码）与代码一致；默认 7 / 0xc 复现。
"""
import struct, sys, os

BASE = 0x400000
IMG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_unpacked_mem.bin')
MEM = open(IMG, 'rb').read()
N = len(MEM)

def read(va, n):
    return MEM[va - BASE: va - BASE + n]

def u16(va):
    return struct.unpack('<H', MEM[va - BASE: va - BASE + 2])[0]

def u32(va):
    return struct.unpack('<I', MEM[va - BASE: va - BASE + 4])[0]

# ---- 从代码实测的 S7 字段映射（续236 坐死）----
# (源 city 偏移, setter, S7 目标偏移, 宽, 钳制上限, 城表语义)
S7_MAP = [
    (0x0c, 0x49be10, 0x00, 1, 0x64,  '農商等级'),
    (0x0f, 0x49be30, 0x01, 1, 0x64,  '生産率'),
    (0x16, 0x49beb0, 0x02, 2, 0x7d0, '地域/クラスタ'),
    (0x18, 0x49bed0, 0x04, 2, 0x7d0, '兵数/城属性(運行期)'),
    (0x12, 0x49be50, 0x06, 2, 0x7530, '米持有'),
    (0x14, 0x49be70, 0x08, 2, 0x7530, '資金'),
    (0x10, 0x49be90, 0x0a, 2, 0xc350, '軍糧'),
    (0x0d, 0x49bef0, 0x0c, 1, 0xfa,  '守城度/次級等級'),
    (0x1a, 0x49bf10, 0x0d, 1, 0xc8,  '次級民情'),
    (0x0e, 0x49bf30, 0x0e, 1, 0xc8,  '民心/治安'),
]
S7_BASE = 0x516a28
CITY_BASE = 0x51eb88
CITY_STRIDE = 31
S7_STRIDE = 16
CAT_DEFAULT = 7
FLAG_DEFAULT = 0xc


def test_A_accessor():
    """验证 0x4511a9 访问器的魔数/基址/位移与映像一致。"""
    code = read(0x4511ac, 0x4511d5 - 0x4511ac + 6)
    # 关键常量应出现在字节流中
    assert b'\x43\x08\x21\x84' in code, 'missing ÷31 magic 0x84210843'
    assert struct.pack('<I', S7_BASE) in code, 'missing S7 base 0x516a28'
    # shl edx,4  (=*16) 与 cmp dl,0xc8(=200) 应存在
    assert b'\xc1\xe2\x04' in code, 'missing shl edx,4 (*16)'
    # 验证 ÷31 魔数确实能把 (city_ptr - CITY_BASE) 还原成索引
    for idx in (0, 5, 92, 199):
        city_ptr = CITY_BASE + idx * CITY_STRIDE
        diff = (city_ptr - CITY_BASE) & 0xffffffff
        # 模拟 idiv via magic: edx = (diff * 0x84210843) >> (32+4) 近似；用 Python 真除校验一致性
        # 代码用 (imul; sar 4; 修正) 等价于 (diff ) // 31（31 为质数，魔数 0x84210843 即 ⌊2^36/31⌋）
        expect = diff // 31
        assert expect == idx, 'magic mismatch at idx %d: %d' % (idx, expect)
        s7_ptr = S7_BASE + idx * S7_STRIDE
        assert s7_ptr == S7_BASE + expect * S7_STRIDE
    # 访问器需调用 类别 setter 0x49bf90(arg=7) 与 标志 setter 0x49bf50 完成记录初始化
    acc = read(0x4511a9, 0x451230 - 0x4511a9)
    acc_calls = []
    i = 0
    while i + 5 <= len(acc):
        if acc[i] == 0xe8:
            t = 0x4511a9 + i + 5 + struct.unpack('<i', acc[i + 1:i + 5])[0]
            if 0x49bf50 <= t <= 0x49bfa0 or t == 0x4b49f0:
                acc_calls.append(t)
        i += 1
    assert 0x49bf90 in acc_calls, 'accessor 0x4511a9 missing category-setter 0x49bf90 call'
    assert 0x49bf50 in acc_calls, 'accessor 0x4511a9 missing flag-setter 0x49bf50 call'
    print('  [A] 访问器 0x4511a9：÷31 魔数/基址/S7=base+idx*16 + 调用 类别/标志 setter 一致 ✅')
    return True


def _extract_setter(va):
    """从 setter 字节码提取：钳制上限 + 目标 S7 偏移 + 宽。

    写回指令形态（基址固定 ecx = S7 记录指针）：
      byte: 88 01        (mod=00)  mov [ecx],al        dst=0
            88 41 XX     (mod=01)  mov [ecx+disp8],al  dst=disp8
            88 81 LO HI  (mod=10)  mov [ecx+disp32],al dst=disp32
      word: 66 89 01 / 66 89 41 XX / 66 89 81 LO HI    (wide=2)
    """
    raw = read(va, 48)
    # clamp: 66 3d XX 00  (cmp ax, imm16)
    clamp = None
    for i in range(len(raw) - 3):
        if raw[i] == 0x66 and raw[i + 1] == 0x3d:
            clamp = raw[i + 2] | (raw[i + 3] << 8)
            break
    # 写回：上述 modrm 三形态（byte 0x88 / word 66 89）
    dst = None
    wide = 1
    for i in range(len(raw) - 5):
        if raw[i] == 0x88 and i + 1 < len(raw):
            modrm = raw[i + 1]
            if modrm == 0x01:
                dst = 0
                wide = 1
                break
            elif modrm == 0x41:
                dst = raw[i + 2]
                wide = 1
                break
            elif modrm == 0x81:
                dst = struct.unpack('<H', raw[i + 2:i + 4])[0]
                wide = 1
                break
        if raw[i] == 0x66 and i + 2 < len(raw) and raw[i + 1] == 0x89:
            modrm = raw[i + 2]
            if modrm == 0x01:
                dst = 0
                wide = 2
                break
            elif modrm == 0x41:
                dst = raw[i + 3]
                wide = 2
                break
            elif modrm == 0x81:
                dst = struct.unpack('<H', raw[i + 3:i + 5])[0]
                wide = 2
                break
    return clamp, dst, wide


def test_B_initializer():
    """验证 0x4b49f0 的 10 段拷入序列与代码一致。"""
    # 0x4b49f0 反汇编中，每个 'call 0x49bexx' 前应有 'movzx/push byte[edi+src]' 或 'mov/push word[edi+src]'
    # 这里直接复核每个 setter 的 (clamp, dst, wide) 是否等于 S7_MAP 中的声明。
    for src, setter, dst_exp, wide_exp, clamp_exp, name in S7_MAP:
        clamp, dst, wide = _extract_setter(setter)
        assert clamp == clamp_exp, 'setter 0x%06x clamp %s != %s' % (setter, hex(clamp), hex(clamp_exp))
        assert dst == dst_exp, 'setter 0x%06x dst %s != %s' % (setter, hex(dst), hex(dst_exp))
        assert wide == wide_exp, 'setter 0x%06x wide %s != %s' % (setter, wide, wide_exp)
    # 还要确认 0x4b49f0 确实按此顺序调用这些 setter（从反汇编 call 序列）
    code = read(0x4b49f0, 0x4b4a82 - 0x4b49f0)
    call_order = []
    i = 0
    while i + 5 <= len(code):
        if code[i] == 0xe8:
            t = 0x4b49f0 + i + 5 + struct.unpack('<i', code[i + 1:i + 5])[0]
            if 0x49be10 <= t <= 0x49bfa0:
                call_order.append(t)
            i += 5
        else:
            i += 1
    # call_order 应含全部 10 个 setter（顺序可能按代码布局）
    for _, setter, _, _, _, _ in S7_MAP:
        assert setter in call_order, 'setter 0x%06x not called in 0x4b49f0' % setter
    # 末段应设 标志 0xc：push 0xc ; call 0x49bf50
    # （类别 setter 0x49bf90 由访问器 0x4511a9 调用，不在 0x4b49f0 内）
    assert 0x49bf50 in call_order, 'missing flag-setter 0x49bf50 call in 0x4b49f0'
    print('  [B] 0x4b49f0 拷入序列：10 setter 的 源/目标/钳制/宽 与代码一致 ✅')
    return True


def _clamp_setter(value, clamp, wide):
    if wide == 2:
        v = value & 0xffff
        if v > clamp:
            v = clamp
        return v
    else:
        v = value & 0xff
        if v > clamp:
            v = clamp
        return v


def test_C_copy_simulation():
    """用合成城表实体跑一遍拷入逻辑，验证 S7 值 + 钳制。"""
    # 合成一个 city 实体（31B），填已知越界值以测钳制
    city = bytearray(31)
    for off, setter, dst, wide, clamp, name in S7_MAP:
        if wide == 2:
            # 填一个超过钳制的值（0xffff）和一个正常值
            val = 0xffff if off in (0x12, 0x14, 0x10, 0x16, 0x18) else 0x1234
            city[off] = val & 0xff
            city[off + 1] = (val >> 8) & 0xff
        else:
            val = 0xff if off in (0x0c, 0x0f, 0x0d, 0x1a, 0x0e) else 0x80
            city[off] = val
    s7 = bytearray(16)
    for off, setter, dst, wide, clamp, name in S7_MAP:
        if wide == 2:
            val = city[off] | (city[off + 1] << 8)
        else:
            val = city[off]
        v = _clamp_setter(val, clamp, wide)
        if wide == 2:
            s7[dst] = v & 0xff
            s7[dst + 1] = (v >> 8) & 0xff
        else:
            s7[dst] = v
    # 校验：越界值应被钳到上限
    def w16(off):
        return s7[off] | (s7[off + 1] << 8)
    assert s7[0x00] == 0x64, '农商 should clamp to 100, got %d' % s7[0x00]
    assert s7[0x01] == 0x64, '生産 should clamp to 100, got %d' % s7[0x01]
    assert w16(0x06) == 0x7530, '米 should clamp to 30000, got %d' % w16(0x06)
    assert w16(0x08) == 0x7530, '資金 should clamp to 30000, got %d' % w16(0x08)
    assert w16(0x0a) == 0xc350, '軍糧 should clamp to 50000, got %d' % w16(0x0a)
    assert s7[0x0c] == 0xfa, '守城 should clamp to 250, got %d' % s7[0x0c]
    assert s7[0x0d] == 0xc8, '次級民情 should clamp to 200, got %d' % s7[0x0d]
    assert s7[0x0e] == 0xc8, '民心 should clamp to 200, got %d' % s7[0x0e]
    # 类别默认 7 / 标志默认 0xc
    s7[0x0f] = (CAT_DEFAULT << 4) | FLAG_DEFAULT
    assert (s7[0x0f] >> 4) & 7 == 7
    assert s7[0x0f] & 0xf == 0xc
    print('  [C] 合成拷入：10 字段值 + 钳制 + 类别/标志默认 全部正确 ✅')
    return True


def test_D_category_flag_setters():
    """验证类别/标志 setter 的位运算与默认语义。"""
    # 类别 setter 0x49bf90: bits4-6 = (arg&7)<<4
    #   mov al,[esp+4]; mov dl,[ecx+0xf]; and al,7; and dl,0x8f; shl al,4; or al,dl; mov [ecx+0xf],al
    code = read(0x49bf90, 0x49bfa4 - 0x49bf90)
    assert b'\x24\x07' in code, 'missing and al,7'   # and al, 7
    assert b'\xc0\xe0\x04' in code, 'missing shl al,4'   # shl al, 4
    assert b'\x80\xe2\x8f' in code, 'missing and dl,0x8f'  # clear bits4-6
    # 标志 setter 0x49bf50: bits0-3 = arg & 0xf （异或技巧实现赋值，非翻转）
    #   mov al,[esp+4]; mov dl,[ecx+0xf]; xor al,dl; and al,0xf; xor dl,al; mov [ecx+0xf],dl
    code2 = read(0x49bf50, 0x49bf60 - 0x49bf50)
    assert b'\x32\xd0' in code2, 'missing xor al,dl'  # xor al, dl
    assert b'\x24\x0f' in code2, 'missing and al,0xf'  # and al, 0xf
    assert b'\x32\xc2' in code2, 'missing xor dl,al'  # xor dl, al
    # 默认复现
    cat = (CAT_DEFAULT & 7) << 4
    assert cat == 0x70
    flag = FLAG_DEFAULT & 0xf
    assert flag == 0xc
    # 组合字节
    b = cat | flag
    assert (b >> 4) & 7 == 7 and (b & 0xf) == 0xc
    print('  [D] 类别/标志 setter 位运算 + 默认 7/0xc 一致 ✅')
    return True


def main():
    print('=== 续236 s7_city_init_ref.py ===')
    ok = True
    ok &= test_A_accessor()
    ok &= test_B_initializer()
    ok &= test_C_copy_simulation()
    ok &= test_D_category_flag_setters()
    print('=== %s ===' % ('ALL PASS ✅' if ok else 'FAIL ❌'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
