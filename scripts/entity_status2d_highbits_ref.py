# -*- coding: utf-8 -*-
# entity_status2d_highbits_ref.py — 武将实体表 +0x2d 高字节 bit4(F4)/bit5-6(F2B) 场景用法解码 (续127)
#
# 证据来源: 2MB 脱壳映像 _unpacked_mem.bin (VA=off+0x400000).
# 前置(续122): +0x2c 是 16-bit 状态字, +0x2d 是其高字节. 本文件解 +0x2d 中「仍待破」的两位:
#   bit4 (0x10 字节 / 0x1000 word) = F4  —— 设/清 setter 0x49a828/0x49a82f
#   bit5-6 (0x60 字节 / 0x6000 word) = F2B —— 2-bit 枚举字段, setter 0x49a840
#
# 关键事实(实测):
#  · F4 setter 0x49a828: `mov eax,[esp+4]; test eax,eax; je 0x49a82f; or byte[ecx+0x2d],0x10; ret4`
#                       clear 0x49a82f: `and word[ecx+0x2c],0xefff; ret4`
#   但 0x49a828 全镜像 E8-调用计数 = 0; packer 0x49a7e0 (46 调用点) 无一处 arg 带 bit4(0x10).
#   => F4 不经任何 traced setter 设置, 只能由「剧本/事件数据流的原始字节写入」置位 (本 build 正常游玩中恒为 0).
#  · F4 消费者(3处): 0x4d50b9 (背叛/谋反判定: F4 置位 -> 强制 return 1), 0x401f58 / 0x402eed (配对例程按 +0x24 匹配后 gate 包含于 F4).
#     => F4 = 谋反/背叛标记 (rebellion flag). 行为角色 HIGH 置信; 本 build 实际恒 0 (near-dead) 是结构性结论.
#  · F2B setter 0x49a840: `mov eax,[esp+4]; cmp ax,4; jae skip; mov dx,word[ecx+0x2c]; and edx,0x9fff; shl eax,0xd; or edx,eax; mov word[+0x2c],dx`
#     = 把值(0..3)写入 bits13-14. 24 调用点, arg 分布 {3:12, 2:5, 1:6} (0 几乎不用).
#  · F2B 消费者(20处, 均 test byte[+0x2d],0x60 判断非零, 如 0x443304 jne->0x4436a0 走异路径): 非零=特殊态, 0=通常态.
#  · 具体赋值规则观测:
#     0x470e40: 比较 this.rank3 与 other.rank3 (=+0x2d 低3位) -> this>other:F2B=1 / this<other:F2B=2 / ==:F2B=3
#     0x40c010: 角色初始化置 F2B=3 (默认/对等)
#     0x40ee90: 循环 per-char -> rank3>=4 且某 flag:F2B=2, 否则 F2B=1
#     => F2B = 序列/身分関係カテゴリ (relative-rank / seniority category). 逐值语义因子系统而异, 须 emu 才唯一钉死 (置信 MEDIUM).
import sys

STRIDE = 47
# +0x2d 字节内位域
BIT_F4   = 0x10   # bit4
MASK_F2B = 0x60   # bit5-6
# +0x2c 16-bit 字内对应位 (=bit8..15)
W_F4  = 0x1000   # bit12
W_F2B = 0x6000   # bit13-14

def get_f4(word):
    return bool(word & W_F4)

def set_f4(word, on=True):
    return word | W_F4 if on else word & ~W_F4 & 0xFFFF

def get_field2b(word):
    """+0x2d.5-.6 = 2-bit 字段 (0..3). word 中位于 bit13-14."""
    return (word & W_F2B) >> 13

def set_field2b(word, v):
    """0x49a840: cmp ax,4; jae skip; and 0x9fff ; shl v,0xd ; or. 拒绝 >=4 (不改动)."""
    if v >= 4:
        return word
    return (word & 0x9FFF) | ((v & 0x3) << 13)

def f2b_from_rank_cmp(this_rank3, other_rank3):
    """0x470e40 还原: this.rank3 与 other.rank3 比较 -> F2B 值."""
    if this_rank3 > other_rank3:
        return 1
    if this_rank3 < other_rank3:
        return 2
    return 3

def betrayal_decision(loyalty, f4_set, byte8_flag, rng_hit):
    """0x4d50b9 行为还原: 返回 1=将背叛/是谋反候补.
    divisor = 2 if (byte[+0x8] & 8) else 1; prob = (100-loyalty)/divisor.
    F4 置位 -> 强制 1; 否则 loyalty<50 -> rng 命中则 1; 否则 0."""
    if f4_set:
        return 1
    if loyalty < 50 and rng_hit:
        return 1
    return 0

def _run_tests():
    ok = 0; tot = 0
    def chk(name, cond):
        nonlocal ok, tot
        tot += 1
        if cond: ok += 1
        else: print(f"  FAIL: {name}")

    # --- F4 位运算 ---
    chk("f4 set->bit12", get_f4(set_f4(0)) and (set_f4(0) & W_F4) == W_F4)
    chk("f4 clear", not get_f4(set_f4(0, False)))
    chk("f4 不影响其他位", (set_f4(0x1234) & ~W_F4) == (0x1234 & ~W_F4))

    # --- F2B 位运算 ---
    chk("field2b 0->0", get_field2b(0) == 0)
    chk("field2b 0x2000==1", get_field2b(0x2000) == 1)
    chk("field2b 0x4000==2", get_field2b(0x4000) == 2)
    chk("field2b 0x6000==3", get_field2b(0x6000) == 3)
    w = set_field2b(0, 2)
    chk("set_field2b 2 -> 0x4000", w == 0x4000)
    w = set_field2b(0xFFFF, 1)
    chk("set_field2b clears 13-14 then sets 1", get_field2b(w) == 1)
    chk("set_field2b 拒绝 >=4", set_field2b(0, 7) == 0)  # 0x49a840 有 cmp ax,4; jae skip

    # --- 0x470e40 相对身分逻辑真值表 ---
    for t in range(8):
        for o in range(8):
            exp = 1 if t > o else (2 if t < o else 3)
            chk(f"rank_cmp({t},{o})=={exp}", f2b_from_rank_cmp(t, o) == exp)
    # 与字节层一致: 设 this.rank3=t, other=o, 把 F2B 值写回 word 后提取 == exp
    for t in range(8):
        for o in range(8):
            exp = f2b_from_rank_cmp(t, o)
            chk(f"byte-extract({t},{o})", get_field2b(set_field2b(0, exp)) == exp)

    # --- 0x4d50b9 背叛判定行为 ---
    chk("F4 置位强制背叛", betrayal_decision(100, True, False, False) == 1)
    chk("忠诚>=50 不背叛", betrayal_decision(80, False, False, False) == 0)
    chk("忠诚<50 rng命中背叛", betrayal_decision(30, False, False, True) == 1)
    chk("忠诚<50 rng未中不屈", betrayal_decision(30, False, False, False) == 0)
    chk("byte[+0x8]&8 不影响纯 F4 路径", betrayal_decision(100, True, True, False) == 1)

    # --- 掩码互补: F4 清 = W_F4 反 ---
    chk("F4 or/clear 互补", (~0xefff & 0xffff) == W_F4)
    chk("F2B or/clear 互补", (~0x9fff & 0xffff) == W_F2B)
    # 高字节 +0x2d 内: bit4=0x10, F2B=0x60
    chk("+0x2d bit4 = 0x10", BIT_F4 == 0x10)
    chk("+0x2d F2B = 0x60", MASK_F2B == 0x60)
    # 字内偏移一致: 高字节 bitN -> word bit(N+8)
    chk("F4 字内 = 0x1000", W_F4 == (BIT_F4 << 8))
    chk("F2B 字内 = 0x6000", W_F2B == (MASK_F2B << 8))

    print(f"RESULT: {ok}/{tot} checks passed")
    return ok == tot

if __name__ == '__main__':
    sys.exit(0 if _run_tests() else 1)
