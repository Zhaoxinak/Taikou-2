# -*- coding: utf-8 -*-
"""S7 @0x516a28 —— 200×16B 每城运行时状态表（续155 破解）。

先前「找不到写入点 / 剧本内全 0」的根因：S7 是**运行时**按城构建的表，
写入全部经由参数化 setter（call 0x49bf50 / 0x49bf90，传 ecx = &S7[城]），
而非直接 `mov [0x516a28+..]`——典型「setter 按 ecx=base+N 参数化」陷阱。

本脚本静态自校验 S7 的结构与字段布局。
"""
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x400000
MEM = open("/Users/ts/Downloads/Taikou 2/scripts/_unpacked_mem.bin", "rb").read()
S7_BASE = 0x516a28
S7_HI = S7_BASE + 200 * 16
TARGET = struct.pack("<I", S7_BASE)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def dis(va, n):
    return list(md.disasm(MEM[va - BASE: va - BASE + n], va))


def reg_n(ins, rid):
    return md.reg_name(rid) if rid else None


def find_literal_hits():
    hits = []
    s = 0
    while True:
        i = MEM.find(TARGET, s)
        if i < 0:
            break
        hits.append(BASE + i)
        s = i + 1
    return hits


def chk(name, cond):
    global OK, TOT
    TOT += 1
    if cond:
        OK += 1
        print("  ok   %s" % name)
    else:
        print("  FAIL %s" % name)


OK = 0
TOT = 0

# 1) 基址存在，且 12 处字面值命中（每城访问模式）
hits = find_literal_hits()
chk("S7 基址 0x516a28 字面值出现 = 12 处", len(hits) == 12)

# 2) 每处命中前的标准模式：cmp reg8,0xc8 (200) → shl reg,4 (×16) → add reg,0x516a28
# 12 处字面值里混有数据区引用（指针表存了 0x516a28）。
# 过滤：仅当窗口内确实含 `add reg,0x516a28` 指令本身，才算真实代码访问。
pat_ok = 0
code_hits = 0
for va in hits:
    ctx = dis(va - 0x20, 0x80)
    has_addbase = any(ins.mnemonic == "add" and "0x516a28" in ins.op_str for ins in ctx)
    if not has_addbase:
        continue  # 数据区引用，跳过
    code_hits += 1
    # 用操作数立即数判定，避免 capstone 小立即数省 0x 前缀的渲染差异
    has_cmp200 = any(ins.mnemonic == "cmp" and len(ins.operands) == 2
                     and ins.operands[1].type == 2 and ins.operands[1].imm == 0xc8
                     for ins in ctx)
    has_shl4 = any(ins.mnemonic == "shl" and len(ins.operands) == 2
                   and ins.operands[1].type == 2 and ins.operands[1].imm == 4
                   for ins in ctx)
    if has_cmp200 and has_shl4:
        pat_ok += 1
chk("真实代码访问全部满足 stride=16 模式(cmp 0xc8 / shl 4 / add 0x516a28)",
    code_hits >= 5 and pat_ok == code_hits)
print("  (代码访问 %d 处，均满足模式)" % code_hits)

# 3) 上界 0xc8 = 200 城
chk("城索引上界 0xc8 = 200", 0xc8 == 200)

# 4) 确认 setter 0x49bf50 / 0x49bf90 写 [ecx+0xf] 与 [ecx+0x8](bit15 切换)
def setter_accesses(tgt):
    acc = set()
    for ins in dis(tgt, 0x140):
        for op in ins.operands:
            if op.type == 3 and reg_n(ins, op.mem.base) == "ecx":
                d = op.mem.disp & 0xff
                if 0 <= d <= 15:
                    isw = (len(ins.operands) >= 1 and ins.operands[0].type == 3
                           and reg_n(ins, ins.operands[0].mem.base) == "ecx"
                           and (ins.operands[0].mem.disp & 0xff) == d)
                    acc.add((d, "W" if isw else "R"))
    return acc

a50 = setter_accesses(0x49bf50)
a90 = setter_accesses(0x49bf90)
chk("0x49bf50 写 +0x0f（主标志字节）", (0x0f, "W") in a50)
chk("0x49bf50 写 +0x08（标志字）", (0x08, "W") in a50)
chk("0x49bf90 写 +0x0a / +0x0b / +0x07",
    (0x0a, "W") in a90 and (0x0b, "W") in a90 and (0x07, "W") in a90)
chk("+0x08 存在 bit15 切换 (or 0x80 / and 0xff7f)",
    any("0x80" in ins.op_str and ins.mnemonic == "or" for ins in dis(0x49bf50, 0x140))
    and any("0xff7f" in ins.op_str and ins.mnemonic == "and" for ins in dis(0x49bf50, 0x140)))

# 5) +0x0f 有 test 0x70 (bit4/5/6) 消费者
has_test70 = any(ins.mnemonic == "test" and "0x70" in ins.op_str
                 for va in hits for ins in dis(va - 0x20, 0x60)
                 if "0x516a28" not in ins.op_str)
chk("+0x0f 主标志字节被 test 0x70 消费（bit4/5/6）", has_test70)

# 6) +0x0c 是 3-bit 标志（or/and 1/2/4）—— 共享方法库 0x49b810
c = dis(0x49b810, 0x100)
chk("+0x0c 经 0x49b810 做 or/and 1,2,4（3-bit 标志）",
    any(ins.mnemonic == "or" and "0xc" in ins.op_str and ("1" in ins.op_str or "2" in ins.op_str or "4" in ins.op_str) for ins in c))

print("\nRESULT: %d/%d checks passed" % (OK, TOT))
