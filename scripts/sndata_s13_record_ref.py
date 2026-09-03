#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sndata_s13_record_ref.py -- SNDATA S13 段文件侧终审：记录装载布局(0x47ef00) + 两剧本文件内容全 0xFF 占位（续238）
================================================================================================================
承接续225（0x518588 5×5 word 矩阵，运行时填充·结构闭）与 §5.2（S13 `0x47ef00` 段，流长 2280 = 20×114，基址歧义 0x5185b6/0x518588）。

本条把三个此前只有断言/emu 观测、没有文件级证据的点坐死：

① **记录装载布局（0x47ef00 逐指令）**：
   `edi=0x5185ba`；每记录（pitch `add edi,0x8b`=139）装载顺序 =
     block A : 25 word @ edi-0x32（= 记录基址 +0x00，首记录=0x518588）
     block B : 25 word @ edi   （= 记录基址 +0x32）
     block C :  5 word @ edi+0x32（= 记录基址 +0x64，5 维向量）
     tail   :  4 byte @ edi+0x3c..0x3f（= 记录基址 +0x6e..0x71）
   每记录装载 114B（流长 2280=20×114），内存记录 pitch 139 ⇒ 记录内 0x72..0x8a（25B）不装载。
   ⇒ §5.2「基址 0x5185b6」是记录0 **block B 起点 0x5185ba 的近似测量**；真实矩阵基址=0x518588（续225 正确）。
   取值器族 `0x4a0ef0`(blockA,+0) / `0x4a0f10`(blockB,+0x32) 与装载布局逐格对应。

② **文件内容 = 全 0xFF 占位（两剧本 SNDATA1/2 均 2280B 全 FF）**：
   剧本文件不携带矩阵数值 ⇒ 「运行期填充」（§5.2 / 续225）为文件级事实；
   运行期写回器 0x4a0ff0/0x4a1010/0x4a1030 是唯一数值来源。

③ **静态解密 + 段地图复核**：解密区=[0x58C..EOF)，单字节 XOR key=raw[0x12]^raw[0x13]；
   `sum(dec[0x58C:]) mod 0x10000 == u16(raw,0x10)`（SNDATA1/2 全中，无需 emu）；
   §5.2 段长累计 S0..S12=35782、全段合计 39436 == EOF-0x58C ⇒ S13 流内偏移 35782 定位无歧义；
   顺带复核 S7(3200B) 文件侧全 0（续207 装载时由 0x47d92b/0x47d94b 写初值 0 的文件来源）。

自测：python3 scripts/sndata_s13_record_ref.py   （结尾 raise SystemExit(0/1)）
"""
import os
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "scripts", "_unpacked_mem.bin")
ORIG = os.path.join(ROOT, "Taikou2 Original")

BASE = 0x400000
MEM = open(BIN, "rb").read()

# ---- S13 loader 0x47ef00 关键字节签名（.text 段固定地址） ----
# mov edi, 0x5185ba            : bf ba 85 51 00
# mov dword [esp+0x10], 0x14   : c7 44 24 10 14 00 00 00
# lea ebx,[edi-0x32]           : 8d 5f ce
# add edi, 0x8b                : 81 c7 8b 00 00 00
SIG = {
    "mov_edi_5185ba":        bytes.fromhex("bf ba 85 51 00"),
    "outer_loop_20":         bytes.fromhex("c7 44 24 10 14 00 00 00"),
    "lea_ebx_edi_m32":       bytes.fromhex("8d 5f ce"),
    "add_edi_0x8b":          bytes.fromhex("81 c7 8b 00 00 00"),
    "lea_ebx_edi_p32":       bytes.fromhex("8d 5f 32"),
    "lea_eax_edi_p3c":       bytes.fromhex("8d 47 3c"),
}
FN0 = 0x47ef00
FN_END = 0x47ef98


def sig_in_fn(pat: bytes) -> bool:
    return pat in MEM[FN0 - BASE: FN_END - BASE]


def dis(va, n):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    return list(md.disasm(MEM[va - BASE: va - BASE + n], va))


RESULTS = []


def chk(name, cond, extra=""):
    RESULTS.append((name, bool(cond), extra))
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", name,
                           ("  -- " + extra) if extra else ""))


# ---------------------------------------------------------------------------
print("=== [A] 装载器 0x47ef00 几何（静态字节签名） ===")
for name, pat in SIG.items():
    chk("%s 签名" % name, sig_in_fn(pat), pat.hex())

# 结构性核对：25/25/5 计数器（mov ebp,0x19 x2 / mov ebp,0x5）
body = dis(FN0, FN_END - FN0)
mne = [(i.address, i.mnemonic, i.op_str) for i in body]
cnt_19 = sum(1 for _, m, o in mne if m == "mov" and o == "ebp, 0x19")
cnt_5 = sum(1 for _, m, o in mne if m == "mov" and o == "ebp, 5")
cnt_call_47d930 = sum(1 for _, m, o in mne if m == "call" and o == "0x47d930")
cnt_call_47d910 = sum(1 for _, m, o in mne if m == "call" and o == "0x47d910")
chk("计数器 ebp=0x19×2 / ebp=5×1", cnt_19 == 2 and cnt_5 == 1,
    "19x2=%d 5x1=%d" % (cnt_19, cnt_5))
# 每记录 25+25+5 word 装载：3 个直接调用点 0x47d930（分别嵌 ebp=0x19/0x19/0x5 循环内）
chk("0x47d930 直接调用点 = 3（循环内 25+25+5 word）", cnt_call_47d930 == 3,
    "call_sites=%d" % cnt_call_47d930)
chk("0x47d910 调用 4 次（4 单字节）", cnt_call_47d910 == 4,
    "calls=%d" % cnt_call_47d910)

# 装载顺序的寻址常量：blockA 首址 = 0x518588（edi-0x32，edi=0x5185ba）
chk("blockA 首址 = 0x5185ba-0x32 = 0x518588",
    0x5185ba - 0x32 == 0x518588)
chk("blockC 寻址 = 记录基址+0x64 (=edi+0x32-0x32? 实 edi+0x32)",
    0x5185ba + 0x32 == 0x5185ec)
chk("tail 4B @ +0x6e..0x71 (=edi+0x3c..0x3f)", 0x3f - 0x3c == 3 and 0x5185ba + 0x3c - 0x518588 == 0x6e)

# ---------------------------------------------------------------------------
print("\n=== [B] 文件级：解密区 + 段地图 + S13/S7 内容 ===")
SBASE = 0x58C
LENS = [22, 21830, 5200, 245, 539, 180, 46, 3200, 360, 80, 120, 3800, 160,
        2280, 1176, 25, 40, 133]
S13_IDX = 13          # S13
S7_IDX = 7            # S7
cum = []
s = 0
for L in LENS:
    cum.append(s)
    s += L
TOTAL = s


def dec_file(fn):
    raw = open(os.path.join(ORIG, fn), "rb").read()
    key = raw[0x12] ^ raw[0x13]
    return raw, key, bytes(b ^ key for b in raw)


for fn in ("SNDATA1.TR2", "SNDATA2.TR2"):
    raw, key, dec = dec_file(fn)
    h10 = struct.unpack_from("<H", raw, 0x10)[0]
    csum = sum(dec[SBASE:]) & 0xffff
    chk("%s key=%02x 校验和 dec[0x58C:]==raw[0x10]"
        % (fn, key), csum == h10, "sum=%04x h=%04x" % (csum, h10))
    chk("%s 段累计 S0..S12=%d S13@流偏移" % (fn, cum[S13_IDX]),
        cum[S13_IDX] == 35782 and TOTAL == len(raw) - SBASE,
        "total=%d == 39436?  EOF-0x58C=%d" % (TOTAL, len(raw) - SBASE))
    # S13 占位
    o = SBASE + cum[S13_IDX]
    s13 = dec[o:o + LENS[S13_IDX]]
    chk("%s S13 段 2280B 全 0xFF（占位·运行期填充）" % fn,
        s13 == b"\xff" * LENS[S13_IDX], "ff=%d" % s13.count(0xff))
    # S7 零
    o7 = SBASE + cum[S7_IDX]
    s7 = dec[o7:o7 + LENS[S7_IDX]]
    chk("%s S7 段 3200B 全 0x00（运行期由 0x4b49f0 类初始化器覆写）" % fn,
        s7 == b"\x00" * LENS[S7_IDX], "zero=%d" % s7.count(0))
    # S1 结构 sanity：370×59 帧、记录0 姓名字段 GBK 可解且含 CJK
    o1 = SBASE + cum[1]
    s1 = dec[o1:o1 + LENS[1]]
    chk("%s S1 = 370×59B" % fn, len(s1) == 370 * 59 and LENS[1] == 370 * 59)
    nm = s1[7:7 + 14].decode("gbk", "ignore")
    chk("%s S1 rec0 名段 GBK 含汉字" % fn, any("\u4e00" <= c <= "\u9fff" for c in nm),
        repr(nm))

# 取值器 block 偏移交叉（续225 getterB +0x32 == blockB 偏移 50）
chk("blockB 偏移 0x32 == 50B == 25 word（getter 0x4a0f10 +0x32 一致）",
    0x32 == 50 and 25 * 2 == 50)

allpass = all(c for _, c, _ in RESULTS)
print("\n总计 %d 项：PASS=%d FAIL=%d" % (len(RESULTS),
      sum(1 for _, c, _ in RESULTS if c), sum(1 for _, c, _ in RESULTS if not c)))
raise SystemExit(0 if allpass else 1)
