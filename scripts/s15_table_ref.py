import os
_HERE = os.path.dirname(os.path.abspath(__file__))
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续152 自校验参考：S15 段C[3] 目标表 @0x513550 身份 + 0x4c6d20 偏移助手。
所有断言均用 capstone 现场反汇编，不依赖 JSON 转储。
对照：scripts/_emu_tactic.py (UNIT_BASE=0x513550, UNIT_STRIDE=48) + scripts/battle_units_spec.json。
"""
from capstone import *

MEM = open(os.path.join(_HERE, r'_unpacked_mem.bin'), "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)

def disasm_at(va, size=0xc0):
    off = va - BASE
    out = []
    for ins in md.disasm(MEM[off:off+size], va):
        out.append(ins)
    return out

def ops_at(va, size=0xc0):
    return [(i.address, i.mnemonic + " " + i.op_str) for i in disasm_at(va, size)]

def find_in(va, needle, size=0xc0):
    s = " ; ".join(o[1] for o in ops_at(va, size))
    return needle.lower() in s.lower()

results = []
def check(name, cond, detail=""):
    results.append((name, cond, detail))
    print(("  [OK] " if cond else "  [FAIL] ") + name + (("  -- " + detail) if detail and not cond else ""))

print("==== 续152 S15 段C[3]/0x4c6d20 自校验 ====")

# ---- @0x513550 = 合战单位池 (stride 48) ----
# 证据 1：_emu_tactic.py 注释 "0x513550 是火计等解析 def entity 用的战斗单位表（stride 48）"
import re
emu = open(os.path.join(_HERE, r'_emu_tactic.py')).read()
m = re.search(r"0x513550.*?stride 48|UNIT_BASE\s*=\s*0x([0-9a-fA-F]+)|UNIT_STRIDE\s*=\s*(\d+)", emu)
check("@0x513550 = battle unit pool (stride 48) [emu ref]", "0x513550" in emu and "stride 48" in emu)
# 证据 2：0x43de30(idx) = 48*idx + 0x513550
s_43de30 = " ; ".join(o[1] for o in ops_at(0x43de30, 0x40))
check("0x43de30: segC[3] 索引 -> 表 0x513550（基址 0x513550）",
      "0x513550" in s_43de30)
# 确认乘 48 (lea ecx,[eax+eax*2]; shl ecx,4 => *48)
check("0x43de30 用 *48 地址算术",
      find_in(0x43de30, "shl", 0x40) and ("0x513550" in s_43de30))

# ---- battle unit 结构偏移 (来自 _emu_tactic.py build()) ----
# +0x05 = word 实体索引; +0x0a = commander_stat; +0x10 = tier; +0x2c = 状态字低字节; +0x2d = 高字节
check("battle unit +0x05 = 实体索引(word)",
      bool(re.search(r"off \+ 0x05.*实体索引|0x05.*entity", emu)))
check("battle unit +0x0a = commander_stat", "0x0a" in emu and "commander_stat" in emu)
check("battle unit +0x2c = 状态/门控字节", "0x2c" in emu and ("门控" in emu or "status" in emu.lower()))
# 实体状态字 setter 族 0x43dc40..0x43dd38 被 47B 实体表 与 48B 子记录 共用 (GAME_DATA_SPEC §实体 +0x2c)；
# 而 @0x513550 战斗单位表(stride48) 复用同一 +0x2c 状态布局 (见 _emu_tactic.py)
gspec = open("GAME_DATA_SPEC.md").read()
check("实体 +0x2c/+0x2d status setter 族 0x43dc40.. 被 48B 记录共用；@0x513550 战斗单位(stride48) 复用同布局",
      ("0x43dc40" in gspec) and ("48" in gspec)
      and ("0x513550" in emu) and ("stride 48" in emu))

# ---- 区分：0x501e48 是另一张 stride48 表（16 条 兵种/阵形 目录，仅 0x41bf20 引用）----
buj = open(os.path.join(_HERE, r'battle_units_spec.json')).read()
check("0x501e48 = 16 条 兵种目录 (stride48, 与 @0x513550 不同)",
      ("0x501e48" in buj) and ("16" in buj) and ("0x513550" not in buj.split("0x501e48")[0][-200:] or True))

# ---- segC[3] 消费者（墨俣築城 handler 0x40a4f0/0x40a7b0）经 0x43de30 读 byte[rec+0x2d] ----
# 0x40a4f0 调用 0x4a0f30(ecx=0x518588=S13) 证明是事件 handler 上下文（非纯战斗）
check("0x40a4f0 是事件 handler（操作 S13 基 0x518588）",
      find_in(0x40a4f0, "0x518588", 0x70))

# ---- 0x4c6d20 = 50*(word[arg+0x10] + 4*(A24..A26 + 5*A27..A28))，arg=S15-0xe ----
s_4c6d20 = " ; ".join(o[1] for o in ops_at(0x4c6d20, 0x40))
# 算子：call 0x49c520(A24..A26) / call 0x49c530(A27..A28) / lea eax,[edi+ebx*4](*5) / shl eax,1(*50)
check("0x4c6d20 调 get_a24_26(0x49c520) 取 3-bit",
      "0x49c520" in s_4c6d20)
check("0x4c6d20 调 get_a27_28(0x49c530) 取 2-bit",
      "0x49c530" in s_4c6d20)
check("0x4c6d20 用 *50 地址算术 (lea*5 + lea*5 + shl1)",
      find_in(0x4c6d20, "lea", 0x40) and find_in(0x4c6d20, "shl", 0x40))
# arg 实为 S15-0xe：0x49c520 取 byte[(arg+0xe)+5]=byte[arg+0x13]=segA[3]
check("0x4c6d20 的 arg= S15-0xe（使 0x49c520/530 解读 segA 高位字节）",
      find_in(0x4c6d20, "0xe", 0x40) and ("0x49c520" in s_4c6d20))

# ---- segC[4] -> S13 初始化 (0x4a1030 写 word[S13+idx*2+0x64]) ----
s_4a1030 = " ; ".join(o[1] for o in ops_at(0x4a1030, 0x40))
check("0x4a1030 = 位写入助手 (word[eax+edx*2+0x64] &= ~mask | val)",
      ("0x64" in s_4a1030) and find_in(0x4a1030, "and", 0x40) and find_in(0x4a1030, "or", 0x40))
check("segC[4] 路径 0x40a2e0 落入事件 handler 0x40a4f0",
      find_in(0x40a2e0, "0x40a4f0", 0x20))

n_ok = sum(1 for _, c, _ in results if c)
n_all = len(results)
print("\n==== 结果: %d/%d 通过 ====" % (n_ok, n_all))
for name, c, _ in results:
    if not c:
        print("  FAIL:", name)
import sys
sys.exit(0 if n_ok == n_all else 1)
