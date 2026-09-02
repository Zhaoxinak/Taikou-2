#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sndata_49b140_ref.py  -- 续224 自测脚本
验证 0x49b140 「city/ref -> 名串解析器」的真实分支语义。

关键结论（基于真实反汇编，非背景日志假设）：
  * 输入：ecx = 指向城数据记录(基址 0x51eb88, stride 31)的指针；ecx==0 视为空。
  * di = (ptr - 0x51eb88) / 31   (魔数 0x84210843 + add/sar4/shr0x1f/add，恰好整除 31)
        == 城数据索引。
  * 四个 `cmp di, N` 是【等值比较】，由 `jne` 跳过（不是 jb/jae 区间分支！）。
  * 四个特殊 di 值各自门控于事件旗(基址 0x5203c0)后返回【同一城名表(0x506fc0, stride 9)
    中 200/201/202/203 号备用名】，而非映射到武将表/国表。
  * 非特殊值 -> 调 0x47a500(di) 取普通城名(名表 idx = di)。
  * ecx==0 -> di 强制为 200 -> 名表 idx 200（字节与 di==0x48 的备用名相同）。

本脚本断言以上可坐实的点，打印 PASS/FAIL，结尾 raise SystemExit(code)。
"""
import pickle, struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x400000
code = open("scripts/_unpacked_mem.bin", "rb").read()
pkl = pickle.load(open("scripts/_insn_addrs.pkl", "rb"))
FUNCS_S = sorted(pkl[1])

def enclosing(va):
    fo = va - BASE
    lo, hi = 0, len(FUNCS_S) - 1
    best = None
    while lo <= hi:
        m = (lo + hi) // 2
        if FUNCS_S[m] <= fo:
            best = FUNCS_S[m]; lo = m + 1
        else:
            hi = m - 1
    return BASE + best if best is not None else None

def next_func(va):
    fo = va - BASE
    for f in FUNCS_S:
        if f > fo:
            return BASE + f
    return BASE + len(code)

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def disasm_func(va):
    f1 = next_func(va)
    return list(md.disasm(code[va - BASE: f1 - BASE], va))

def calls_of(tgt):
    out = set(); off = 0
    while True:
        idx = code.find(b'\xe8', off)
        if idx < 0:
            break
        rel = struct.unpack("<i", code[idx + 1: idx + 5])[0]
        va = BASE + idx + 5 + rel
        if va == tgt:
            out.add(BASE + idx)
        off = idx + 1
    return out

# ---- 精确 x86 32-bit 语义模拟 di 计算（验证魔数整除 31） ----
MASK = 0xffffffff
SIGN = 0x80000000
def s32(x):
    x &= MASK
    return x - MASK if x & SIGN else x
def u32(x):
    return x & MASK
def sar32(x, s):
    return u32(s32(x) >> s)
def shr32(x, s):
    return u32(x) >> s
def compute_di(ptr):
    ecx = s32(ptr - 0x51eb88)
    eax_s = s32(0x84210843)
    prod = eax_s * ecx                      # 64-bit signed
    edx = u32((prod >> 32) & MASK)
    eax = u32(prod & MASK)
    edx = u32(s32(edx) + ecx)               # add edx, ecx
    edx = sar32(edx, 4)                     # sar edx, 4
    eax = shr32(edx, 0x1f)                  # mov eax,edx ; shr eax,0x1f
    edx = u32(s32(edx) + s32(eax))          # add edx, eax
    return edx & 0xff                       # movzx di, dl

# =================== 测试 ===================
results = []
def check(name, cond, detail=""):
    results.append((name, cond, detail))
    print(("PASS " if cond else "FAIL ") + name + (("  -- " + detail) if detail else ""))

insns = disasm_func(0x49b140)
mn = {i.address: i for i in insns}

# 1) 四个 cmp di, N 的取值与地址（按出现顺序）
cmps = []
for i in insns:
    if i.mnemonic == 'cmp' and i.op_str.startswith('di, '):
        imm = int(i.op_str.split(',')[1].strip(), 0)
        cmps.append((i.address, imm))
check("four_cmp_di_present", len(cmps) == 4,
      "found %d cmp di" % len(cmps))
check("cmp_values_48_66_64_7c",
      [v for _, v in cmps] == [0x48, 0x66, 0x64, 0x7c],
      str([hex(v) for _, v in cmps]))

# 每个 cmp 后紧跟 jne（等值跳过，非区间分支）
sorted_addrs = sorted(mn.keys())
addr_pos = {a: i for i, a in enumerate(sorted_addrs)}
all_jne = True
for (addr, imm) in cmps:
    pos = addr_pos[addr]
    nxt = mn[sorted_addrs[pos + 1]]  # 下一条真实指令
    if nxt.mnemonic != 'jne':
        all_jne = False
check("cmp_followed_by_jne_equality", all_jne,
      "每个 cmp di 后都是 jne（等值门控，非 jb/jae 区间）")

# 2) 各 di 值返回的字符串地址
ret_map = {
    0x48: 0x5076c8,   # 0x49b1a9 mov eax, 0x5076c8
    0x66: 0x5076d1,   # 0x49b1d7 mov eax, 0x5076d1
    0x64: 0x5076da,   # 0x49b216 mov eax, 0x5076da
    0x7c: 0x5076e3,   # 0x49b234 mov eax, 0x5076e3
}
# 找到函数里 "mov eax, 0x5076xx" 的指令，确认它们存在于各分支返回路径
mov_eax_targets = {}
for i in insns:
    if i.mnemonic == 'mov' and i.op_str.startswith('eax, 0x'):
        mov_eax_targets[int(i.op_str.split(',')[1].strip(), 0)] = i.address
for di_val, ret_addr in ret_map.items():
    check("ret_str_for_di_0x%02x" % di_val,
          ret_addr in mov_eax_targets,
          "0x%X present at 0x%X" % (ret_addr, mov_eax_targets.get(ret_addr, 0)))

# 3) 四个返回串 == 城名表 0x506fc0 (stride 9) 的 idx 200/201/202/203
NAME_BASE = 0x506fc0
NAME_STRIDE = 9
alias_idx = {0x5076c8: 200, 0x5076d1: 201, 0x5076da: 202, 0x5076e3: 203}
ok_alias = True
for saddr, ni in alias_idx.items():
    expect = NAME_BASE + ni * NAME_STRIDE
    if expect != saddr:
        ok_alias = False
    check("alias_str_0x%X_is_nametable_idx_%d" % (saddr, ni),
          expect == saddr,
          "0x506fc0+%d*9 = 0x%X" % (ni, expect))
check("four_alias_are_nametable_200_203", ok_alias)

# 4) 默认路径调用 0x47a500（两处: ecx==0 路径 0x49b24b, 普通路径 0x49b275）
calls_47a500 = [i.address for i in insns if i.mnemonic == 'call' and i.op_str == '0x47a500']
check("calls_47a500_default",
      len(calls_47a500) >= 1,
      "call sites: %s" % [hex(a) for a in calls_47a500])

# 5) 0x47a500 用 0x506fc0 + idx*9 取城名（确认默认路径就是普通城名）
ins47 = disasm_func(0x47a500)
uses_nametable = any(
    i.mnemonic == 'lea' and '0x506fc0' in i.op_str for i in ins47)
check("47a500_uses_nametable_506fc0", uses_nametable)

# 6) 本函数只引用城数据表基 0x51eb88 + 魔数 0x84210843；不引用武将表 0x519868 / 国表 0x5179b8
refs = set()
for i in insns:
    for op in (i.op_str or '').split(','):
        op = op.strip()
        if op.startswith('0x') and 'ptr' not in op:
            try:
                refs.add(int(op, 0))
            except ValueError:
                pass
check("ref_citydata_51eb88", 0x51eb88 in refs)
check("ref_magic_84210843", 0x84210843 in refs)
check("no_ref_warrior_519868",
      not any(0x519868 <= r <= 0x519868 + 0x47b + 16 for r in refs),
      "warrior table 0x519868 未在本函数出现")
check("no_ref_country_5179b8",
      not any(0x5179b8 <= r <= 0x5179b8 + 0x40 for r in refs),
      "country table 0x5179b8 未在本函数出现")

# 7) 调用者包含加载路径 0x451860 的调用点 0x4518ca
c = calls_of(0x49b140)
check("called_by_loader_451860", 0x4518ca in c and enclosing(0x4518ca) == 0x451860,
      "0x4518ca enclosing=0x%X" % (enclosing(0x4518ca) if 0x4518ca in c else 0))

# 8) 魔数整除 31：di 精确等于城数据索引
ok_div = all(compute_di(0x51eb88 + k * 31) == k for k in (0, 1, 72, 100, 102, 124, 199, 200))
for k in (0, 1, 72, 100, 102, 124, 199, 200):
    check("di_eq_index_%d" % k, compute_di(0x51eb88 + k * 31) == k,
          "di=0x%X" % compute_di(0x51eb88 + k * 31))
check("magic_divides_by_31", ok_div, "di == (ptr-0x51eb88)/31 对所有样本成立")

allpass = all(c for _, c, _ in results)
print("\n%d/%d PASS" % (sum(1 for _, c, _ in results if c), len(results)))
raise SystemExit(0 if allpass else 1)
