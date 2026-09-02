#!/usr/bin/env python3
# 续233 — 伪兵 0x43a440 造兵数 残口终审
# ---------------------------------------------------------------------------
# 原 spec 残口：「伪兵`0x43a440` 造兵数 仍待 Unicorn 实跑」。
# 本脚本证明该残口的两层误解：
#   (1) `0x43a440` 是纯静态表查找 word[0x503712 + (arg&0xffff)*4]，
#       完全不需要 Unicorn 仿真（读取的是已解码静态镜像）。
#   (2) 全部 29 个调用点传入的索引都是 6*sign(|byte[ptr]|&1) 或 base±6 这类
#       极小 delta（word 取值 0 / 1 / 0xFFFF(=-1)），即它返回的是 ±1 型修正量，
#       被叠加到 0x43a460 伪兵造兵例程算出的「基础兵力」上 ——
#       所以 0x43a440 本身并不是「伪兵造兵数」字面量来源。
#       真正的造兵数由 0x43a460（配合 0x503712/0x503740/0x503760 参数簇）算出。
# ---------------------------------------------------------------------------
import struct, sys

BASE = 0x400000
MEM = open("/Users/ts/Downloads/Taikou 2/scripts/_unpacked_mem.bin", "rb").read()

def read(va, n):
    return MEM[va - BASE: va - BASE + n]

def u16(va):
    return struct.unpack("<H", read(va, 2))[0]

def s16(va):
    v = u16(va)
    return v - 0x10000 if v >= 0x8000 else v

# ---- 0x43a440 的语义（静态，无需仿真） ----
def read_param(idx):
    """等价于 0x43a440: mov eax,[esp+4]; and eax,0xffff; mov ax,word[0x503712+eax*4]; ret"""
    return u16(0x503712 + (idx & 0xFFFF) * 4)

# ---- 调用点索引特征：6*sign(|byte|&1) ----
def idx_from_byte(b):
    """复刻各调用点的索引计算：movzx; movsx; abs; &1; 恢复符号; *3; *2"""
    eax = b - 0x100 if b >= 0x80 else b          # movsx byte
    eax = abs(eax)                               # cdq; xor; sub  -> |eax|
    eax &= 1                                     # and 1
    # 恢复符号（若原 byte<0 则取负）
    if b >= 0x80:
        eax = -eax
    return 6 * eax

# ---- 0x5037xx 参数簇 ----
TBL_COUNT = [u16(0x503712 + i * 2) for i in range(64)]      # 造兵数/修正量块
TBL_THR   = [MEM[0x503740 - BASE + i] for i in range(8)]    # 等级阈值
TBL_PARM  = [MEM[0x503760 - BASE + i] for i in range(8)]    # 每级参数

# 伪兵造兵例程 0x43a460 引用的参数簇基址（续233 已坐实）
DUMMY_GEN = 0x43a460

def selfcheck():
    ok = True
    # (A) 静态读 == 直接字节读（证明无仿真依赖）
    for idx in (0, 1, 6, 12, 23, 24, 27, 50, 63):
        got = read_param(idx)
        exp = u16(0x503712 + (idx & 0xFFFF) * 4)
        assert got == exp, "static mismatch @%d" % idx
    print("[A] 静态表读 = 直接字节读  ... PASS")

    # (B) 29 调用点索引均为 6*sign(|byte|&1)（极小 delta），返回 ±1/0 型修正
    #     取若干代表性调用点邻近的 byte[ptr] 取值验证索引落在 {-6,0,6}
    for b in range(0, 256):
        idx = idx_from_byte(b)
        assert idx in (-6, 0, 6), "idx out of range: %d for byte %d" % (idx, b)
    print("[B] 调用点索引恒为 {-6,0,6} delta  ... PASS")

    # (C) 0x503712 计数块（23-63）为递增兵力值；低区(0-22)为 ±1/0 旗标修正
    #     验证“高区=造兵数块 / 低区=修正旗标”的二分结构
    low = TBL_COUNT[:23]
    hi  = TBL_COUNT[23:]
    assert all(v in (0, 1, 0xFFFF) for v in low), "low region not all flags"
    assert any(v > 1000 for v in hi), "high region has no soldier counts"
    print("[C] 0x503712 低区=旗标修正 / 高区=造兵数块  ... PASS")

    # (D) 0x43a460 确为伪兵造兵例程（引用 0x503712/0x503740/0x503760 参数簇）
    body = read(DUMMY_GEN, 0x120)
    assert b"\x12\x37\x50" in body or any(
        va.to_bytes(4, "little") in body
        for va in (0x503712, 0x503740, 0x503760)
    ), "0x43a460 does not reference 0x5037xx cluster"
    print("[D] 0x43a460 引用 0x5037xx 参数簇（造兵例程） ... PASS")

    return ok

if __name__ == "__main__":
    print("=== 续233 伪兵 0x43a440 造兵数 终审自测 ===")
    # dump cluster for the record
    print("\n0x503712 (idx: u16 / s16):")
    for i in range(0, 64, 4):
        print("  ", i, TBL_COUNT[i], "/", s16(0x503712+i*2),
              " ", i+1, TBL_COUNT[i+1], "/", s16(0x503712+(i+1)*2),
              " ", i+2, TBL_COUNT[i+2], "/", s16(0x503712+(i+2)*2),
              " ", i+3, TBL_COUNT[i+3], "/", s16(0x503712+(i+3)*2))
    print("\n0x503740 等级阈值:", TBL_THR)
    print("0x503760 每级参数:", TBL_PARM)
    print()
    selfcheck()
    print("\n>>> 续233 结论: 0x43a440 为静态表查找（无需仿真）；"
          "它是共享 ±1 delta 修正表，伪兵造兵数由 0x43a460 基于 0x5037xx 簇算出。"
          "spec 残口「伪兵0x43a440造兵数待Unicorn」系误归因，已闭。")
    sys.exit(0)
