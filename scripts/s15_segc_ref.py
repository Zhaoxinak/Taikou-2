# -*- coding: utf-8 -*-
"""
续151 段C(6字节) + segA 高位 bit(A24..A28) 访问器 自校验参考实现。
所有结论均基于 capstone 现场反汇编，非 JSON 转储。

段C 布局（S15 基址 0x5203c0，段C @ +0x13..+0x18）：
  segC[0] = S13 目標記録索引 (0..19, 0x14=none)  -> 表 @0x518588 stride 0x8b(139)
  segC[1]||segC[2] = 16-bit 打包事件参数 (idx1=高字节, idx2=低字节)
  segC[3] = 表 @0x513550 stride 48 索引 (then byte[rec+0x2d] 读状态)
  segC[4] = ×1000 喂入 S13 记录初始化 (0x4a1030)
  segC[5] = 事件内计数/标志（桶狭間 handler 0x408dc0 中 cmp）

segA 高位（byte +0x5 = segA 第3字节 = bit A24..A31）：
  A24..A26 = 3-bit 计数器(0..7)  get 0x49c520 / set 0x49c540
  A27,A28  = 2-bit 计数器(0..3)  get 0x49c530 / set 0x49c560
  A29      = 1-bit 标志           set 0x49c580
  A30,A31  = 个体事件标志         (get_a/0x49c390 按 bit 测)
  5-bit 组合(A24..A28) 作表索引（fn 0x4c6d20）
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

import os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)


def disasm_at(va, n=0x60):
    off = va - BASE
    return list(md.disasm(MEM[off:off + n], va))


def disasm_fn(va, n=0x200):
    """反汇编从 va 开始的整段（到 ret 或 n 上限）。"""
    off = va - BASE
    return list(md.disasm(MEM[off:off + n], va))


CHECKS = []
def check(name, cond):
    CHECKS.append((name, bool(cond)))


# ---- 段C 访问器 ----
ins = disasm_at(0x49c410, 0x18)
check("get_c 读 byte[ecx+eax+0x13]",
      any(it.mnemonic == "mov" and "0x13" in it.op_str and "ecx" in it.op_str for it in ins))
ins = disasm_at(0x49c500, 0x18)
check("set_c 写 byte[eax+ecx+0x13]",
      any(it.mnemonic == "mov" and "0x13" in it.op_str and "ecx" in it.op_str for it in ins))

# ---- segC[0] -> S13 索引 (fn 0x413f1d) ----
f = disasm_fn(0x413f1d, 0x60)
s = " ".join("%s %s" % (it.mnemonic, it.op_str) for it in f)
check("segC[0] 读者 0x413f1d: 调 get_c 且解引用 S13 表 0x518588",
      ("call 0x49c410" in s) and ("0x518588" in s) and ("0x14" in s))

# ---- 0x419fb0 = S13 索引校验 (×139+0x518588, 再校 0x172 武将哨兵) ----
f = disasm_fn(0x419fb0, 0x60)
s = " ".join("%s %s" % (it.mnemonic, it.op_str) for it in f)
check("0x419fb0: S13 索引->记录 + 武将哨兵 0x172",
      ("0x518588" in s) and ("0x172" in s))

# ---- 0x43de30 = ×48 + 0x513550 (segC[3] 表) ----
f = disasm_fn(0x43de30, 0x40)
s = " ".join("%s %s" % (it.mnemonic, it.op_str) for it in f)
check("0x43de30: segC[3] 索引 -> 表 0x513550 stride 48",
      ("0x513550" in s) and ("0x14" in s))

# ---- segC[1]||segC[2] 16-bit 打包 (fn 0x419ec0: (segC[1]<<8)|segC[2]) ----
f = disasm_fn(0x419ec0, 0x40)
s = " ".join("%s %s" % (it.mnemonic, it.op_str) for it in f)
check("segC[1]<<8 | segC[2] 打包 (0x419ec0)",
      ("shl eax, 8" in s) and ("add eax, ecx" in s) and ("call 0x49c410" in s))

# ---- 0x419ef0 写 segC[1] 与 segC[2] (两路 set_c, 高/低字节拆分) ----
f = disasm_fn(0x419ef0, 0x40)
c = sum(1 for it in f if it.op_str == "0x49c500")
check("0x419ef0: 同时写 segC[1] 与 segC[2] (2× set_c)",
      c == 2 and ("and eax, 0xff" in " ".join("%s %s"%(it.mnemonic,it.op_str) for it in f)))

# ---- segC[4] ×1000 -> S13 初始化 (fn 0x40a2e0) ----
f = disasm_fn(0x40a2e0, 0x90)
s = " ".join("%s %s" % (it.mnemonic, it.op_str) for it in f)
check("segC[4]: ×1000 喂入 S13 初始化 (0x4a1030 @ 0x518588)",
      ("0x518588" in s) and ("shl esi, 3" in s) and ("call 0x4a1030" in s))

# ---- segA 高位访问器 ----
f = disasm_fn(0x49c520, 0x18)
s = " ".join("%s %s" % (it.mnemonic, it.op_str) for it in f)
check("0x49c520 = get A24..A26 (byte[+5]&7)",
      ("byte ptr [ecx + 5]" in s) and ("and eax, 7" in s))
f = disasm_fn(0x49c530, 0x18)
s = " ".join("%s %s" % (it.mnemonic, it.op_str) for it in f)
check("0x49c530 = get A27,A28 (byte[+5]>>3 &3)",
      ("byte ptr [ecx + 5]" in s) and ("shr eax, 3" in s) and ("and eax, 3" in s))
f = disasm_fn(0x49c540, 0x18)
s = " ".join("%s %s" % (it.mnemonic, it.op_str) for it in f)
check("0x49c540 = set A24..A26 (低3位替换)",
      ("byte ptr [ecx + 5]" in s) and ("and al, 7" in s))
f = disasm_fn(0x49c560, 0x18)
s = " ".join("%s %s" % (it.mnemonic, it.op_str) for it in f)
check("0x49c560 = set A27,A28 (bits3-4)",
      ("byte ptr [ecx + 5]" in s) and ("and al, 3" in s) and ("shl al, 3" in s) and ("0xe7" in s))

# ---- A24..A28 组合 5-bit 作表索引 (fn 0x4c6d20) ----
f = disasm_fn(0x4c6d20, 0x40)
s = " ".join("%s %s" % (it.mnemonic, it.op_str) for it in f)
check("0x4c6d20: 组合 A24..A28 (调 0x49c520 与 0x49c530)",
      ("call 0x49c520" in s) and ("call 0x49c530" in s))

# ---- 运行 ----
ok = 0
for name, cond in CHECKS:
    print("  [%s] %s" % ("OK" if cond else "FAIL", name))
    ok += 1 if cond else 0
print("\n== s15_segc_ref: %d/%d 通过 ==" % (ok, len(CHECKS)))
assert ok == len(CHECKS), "自校验未全过"
