# -*- coding: utf-8 -*-
"""entity_status_semantics_ref.py
实体尾部状态字段的「语义」层闭合（续123）：
  1) +0x29 忠诚(0..100) 的阈值语义：
       - 50  : 0x45a384 `cmp byte[+0x29],0x32; jb` → 忠诚<50 = 可被劝诱/拉拢候选
       - 100 : 0x4aa72d `cmp byte[+0x29],0x64; je` → 忠诚==100 = 绝对忠诚, 排除于策反
  2) +0x2d 低3位 = 身分代码(0..7)，与 BSDATA 身分代码同表（GAME_DATA_SPEC §1.2）：
       0=无 1=足轻组头 2=足轻工头 3=足轻头 4=家老 5=组头 6=家臣 7=大名
     setter 0x49a7e0(ptr,val) 写入 word[+0x2c] 的 bits8-10；
     consumers: 0x4477b0(选 [target,target+1] 档), 0x4d3eb0(精确匹配同身分), 0x4bd230(要求 rank3<3)
自测常量均来自二进制静态反汇编实证。
"""
import sys

# ---- 复刻 续122 的位操作（独立实现，避免 import 路径问题）----
STRIDE = 47
MASK_RANK3 = 0x07
BIT_DEAD  = 0x80
W_RANK3   = 0x0700
W_DEAD    = 0x8000

def set_loyalty(v):       return max(0, min(int(v), 100)) & 0xff
def get_rank3(word):      return (word >> 8) & MASK_RANK3
def set_rank3(word, v):   return (word & 0xF8FF) | ((int(v) & 0x07) << 8)

# ---- 语义常量（二进制实证 + BSDATA 同表）----
LOYALTY_MAX = 100
LOY_RECRUIT_THRESHOLD = 50   # 0x45a384
LOY_FULL = 100               # 0x4aa72d

# 身分代码 → 中文名（BSDATA §1.2 已校验；信长=7=大名 与 0x40fedb push7 一致）
STATUS_CODE_NAMES = {
    0: "无",
    1: "足轻组头",
    2: "足轻工头",
    3: "足轻头",
    4: "家老",
    5: "组头",
    6: "家臣",
    7: "大名",
}

# 实证到的 身分代码 赋值（setter 0x49a7e0 调用点 push 常量）
OBSERVED_SETTER_VALUES = {0, 1, 3, 4, 5, 7}
# 消费者地址
CONSUMER_RANGE   = 0x4477b0   # 选 [target, target+1] 身分档
CONSUMER_MATCH   = 0x4d3eb0   # 精确匹配同身分
CONSUMER_PRED    = 0x4bd230   # 谓词: 要求 rank3 < 3
SETTER_RANK3     = 0x49a7e0   # set_rank3(ptr, val)

def check(name, cond):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name}")
    return cond

def main():
    print("=== entity_status_semantics_ref 自测 ===")
    n = 0; ok = 0
    def T(name, cond):
        nonlocal n, ok
        n += 1; ok += 1 if check(name, cond) else 0

    # 1) 身分代码空间 0..7 与命名
    T("身分代码为 0..7 八档", set(STATUS_CODE_NAMES) == set(range(8)))
    T("大名=7 与 setter push7 一致", STATUS_CODE_NAMES[7] == "大名")
    T("所有赋值观测值落在 0..7", all(0 <= v <= 7 for v in OBSERVED_SETTER_VALUES))

    # 2) set_rank3 仅改 bits8-10，低字节不动
    w = set_rank3(0x00AB, 7)
    T("set_rank3 hi低3位=7 且低字节保留", ((w >> 8) & 7) == 7 and (w & 0xFF) == 0xAB)
    T("set_rank3 写 0x0700 位域", (w & W_RANK3) == 0x0700)
    T("get_rank3 还原", get_rank3(w) == 7)
    # 覆盖写不残留
    w2 = set_rank3(w, 0)
    T("set_rank3(0) 清 bits8-10", (w2 & W_RANK3) == 0 and get_rank3(w2) == 0)

    # 3) 忠诚夹紧到 100
    T("set_loyalty 夹紧上界100", set_loyalty(250) == 100)
    T("set_loyalty 夹紧下界0", set_loyalty(-5) == 0)
    T("set_loyalty 中间值透传", set_loyalty(47) == 47)

    # 4) 忠诚阈值语义常量
    T("招募阈值=50", LOY_RECRUIT_THRESHOLD == 50)
    T("满忠诚=100", LOY_FULL == 100)
    # 行为语义：<50 可劝诱；==100 不可策反
    def is_recruitable(loy):  return loy < LOY_RECRUIT_THRESHOLD   # 0x45a384 jb
    def is_bribable(loy):     return loy != LOY_FULL               # 0x4aa72d je(skip)
    T("忠诚49 可劝诱", is_recruitable(49) is True)
    T("忠诚50 不可劝诱(阈值不含等)", is_recruitable(50) is False)
    T("忠诚100 不可策反", is_bribable(100) is False)
    T("忠诚99 可策反", is_bribable(99) is True)

    # 5) 死标志位不干扰身分码提取
    wd = set_rank3(0, 7) | W_DEAD
    T("已故位(bit7高字节) 与 身分码 共存不混淆", get_rank3(wd) == 7 and bool(wd & W_DEAD))

    print(f"\nRESULT: {ok}/{n} checks passed")
    return 0 if ok == n else 1

if __name__ == "__main__":
    raise SystemExit(main())
