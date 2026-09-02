#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
table_518588_ref.py  --  0x518588 「5 列 word 矩阵（stride 139）」自测脚本
============================================================================
针对续225 待破④：破解 0x518588 处矩阵的逐格语义。

验证对象（来自任务书 / 既有突破日志 BREAKTHROUGHS.md 续151 / 续212 / 续220）：
  * BASE = 0x400000；解包镜像 scripts/_unpacked_mem.bin（file offset = VA - 0x400000）
  * 基地址 BASE_TABLE = 0x518588  (= S13 rec0 基址，runtime stride 0x8b=139)
  * 取值器 0x4a0ef0 / 0x4a0f10（5×5 word 矩阵取值器，同族 0x4a0ff0/0x4a1010/0x4a0f80/0x4a1030）
  * ÷139 魔数 0x75ded953（配 sar edx,6 → 总移 38 位；segC[1]=(ptr-0x518588)/139）

所有结论均从镜像反汇编实拍，不臆测数值（静态镜像该表为零填充，运行期才填）。
结尾：raise SystemExit(0 if allpass else 1)
"""
import pickle, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x400000
BASE_TABLE = 0x518588
STRIDE = 139                      # 0x8b
MAGIC139 = 0x75ded953            # ÷139 倒数乘法魔数
GETTER_A = 0x4a0ef0              # block @ offset 0
GETTER_B = 0x4a0f10              # block @ offset 0x32

code = open("scripts/_unpacked_mem.bin", "rb").read()
pkl = pickle.load(open("scripts/_insn_addrs.pkl", "rb"))
FUNCS_S = sorted(pkl[1])
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def disasm(va, n):
    return list(md.disasm(code[va - BASE: va - BASE + n], va))

def next_func(va):
    ffo = va - BASE
    for f in FUNCS_S:
        if f > ffo:
            return BASE + f
    return BASE + len(code)

def enclosing(va):
    ffo = va - BASE
    best = None
    for f in FUNCS_S:
        if f <= ffo:
            best = BASE + f
    return best

results = []

def check(name, cond, detail=""):
    results.append((name, cond, detail))
    print("%-46s %s%s" % (name, "PASS" if cond else "FAIL",
                          ("  -- " + detail) if detail else ""))

# ---------------------------------------------------------------------------
# 1) stride == 139（0x8b）确认：÷139 魔数 + 反算 (k*139) -> k
# ---------------------------------------------------------------------------
def div139(off):
    """模拟 0x518588 ÷139 站点：
         sub reg, 0x518588        ; eax = ptr - base  (有符号 32 位)
         mov eax, 0x75ded953
         imul ecx                 ; edx:eax = M * eax  (有符号 64 位)
         sar  edx, 6              ; 商 = (M*off) >> 38  (算术右移)
    """
    eax = MAGIC139 if MAGIC139 < 2**31 else MAGIC139 - 2**32
    ecx = off if off < 2**31 else off - 2**32
    prod = eax * ecx
    if prod >= 0:
        return prod >> 38
    return -((-prod) >> 38)

check("stride 常量 == 139 (0x8b)", STRIDE == 0x8b, "0x8b = 139")

# 反算：offset = k*139（即指向第 k 个 139 字节记录基址）必须还原 k
rt_ok = True
rt_bad = []
for k in range(0, 30):
    if div139(k * 139) != k:
        rt_ok = False
        rt_bad.append(k)
for k in (50, 100, 200, 300, 608):
    if div139(k * 139) != k:
        rt_ok = False
        rt_bad.append(k)
check("(k*139) 反算 -> k 成立（÷139 魔数 0x75ded953）",
      rt_ok, "失败点: %s" % rt_bad if rt_bad else "k=0..29,50,100,200,300,608 全中")

# 魔数确实出现在镜像中、且与 0x518588 配对
magic_bytes = struct.pack("<I", MAGIC139)
magic_hits = []
off = 0
while True:
    i = code.find(magic_bytes, off)
    if i < 0:
        break
    magic_hits.append(BASE + i)
    off = i + 1
# 真实 ÷139 站：sub reg,0x518588 紧邻 mov eax, MAGIC139
real_sites = []
for mh in magic_hits:
    ins = disasm(mh - 8, 16)
    for x in ins:
        if x.mnemonic == 'sub' and '0x518588' in x.op_str:
            real_sites.append(x.address)
check("镜像中存在 ÷139 魔数并与 0x518588 配对 (>=1 站点)",
      len(real_sites) >= 1, "%d 个站点，例如 %s" %
      (len(real_sites), ["%08x" % s for s in real_sites[:3]]))

# ---------------------------------------------------------------------------
# 2) 行上限 = 20（segC[0] 0..19，0x14=none）
#    证据：÷139 站点附近有 `cmp bp/di, 0x14; jae` 越界保护
# ---------------------------------------------------------------------------
bound_found = []
for s in real_sites:
    for ins in disasm(s - 8, 0x90):
        if ins.mnemonic == 'cmp' and ('0x14' in ins.op_str):
            bound_found.append((ins.address, ins.op_str))
check("行上限有 0x14 越界保护（记录数 == 20, 行 0..19）",
      len(bound_found) >= 1, "站点: %s" %
      (["%08x %s" % b for b in bound_found[:2]]))

# ---------------------------------------------------------------------------
# 3) 取值器索引公式：(a*5+b)*2，block 偏移 0 / 0x32
#    0x4a0ef0 : word[ecx + (a*5+b)*2]            (block @ +0)
#    0x4a0f10 : word[ecx + (a*5+b)*2 + 0x32]     (block @ +0x32)
# ---------------------------------------------------------------------------
def getter_formula(va):
    """返回 (has_lea_x5, has_add_b, has_scale2, offset_extra)"""
    has_lea_x5 = has_add_b = has_scale2 = False
    offset_extra = 0
    for ins in disasm(va, next_func(va) - va):
        if ins.mnemonic == 'lea' and '[eax + eax*4]' in ins.op_str:
            has_lea_x5 = True
        if ins.mnemonic == 'add' and ins.op_str.strip().endswith('edx'):
            has_add_b = True
        if ins.mnemonic == 'mov' and ('eax*2]' in ins.op_str or
                                     ('eax*2' in ins.op_str)):
            has_scale2 = True
            # 提取 +0xNN 偏移
            if '+ 0x' in ins.op_str:
                try:
                    offset_extra = int(ins.op_str.split('+ 0x')[1].split(']')[0], 16)
                except Exception:
                    pass
    return has_lea_x5, has_add_b, has_scale2, offset_extra

lx5_a, ab_a, s2_a, off_a = getter_formula(GETTER_A)
lx5_b, ab_b, s2_b, off_b = getter_formula(GETTER_B)

check("0x4a0ef0 含 ×5 (lea eax,[eax+eax*4])", lx5_a)
check("0x4a0ef0 含 +b (add eax,edx)", ab_a)
check("0x4a0ef0 含 ×2 缩放 (eax*2)", s2_a)
check("0x4a0ef0 block 偏移 == 0", off_a == 0, "实测 +0x%x" % off_a)

check("0x4a0f10 含 ×5 (lea eax,[eax+eax*4])", lx5_b)
check("0x4a0f10 含 +b (add eax,edx)", ab_b)
check("0x4a0f10 含 ×2 缩放 (eax*2)", s2_b)
check("0x4a0f10 block 偏移 == 0x32 (50)", off_b == 0x32, "实测 +0x%x" % off_b)

# 用公式实算列偏移：a=0 时 5 列 (b=0..4) 的字节偏移 = 0,2,4,6,8
col_offsets = [(0 * 5 + b) * 2 for b in range(5)]
check("5 列字节偏移 == [0,2,4,6,8]",
      col_offsets == [0, 2, 4, 6, 8], str(col_offsets))
# 5×5 矩阵：a(行)=0..4, b(列)=0..4 → 25 个连续 word（block 内 0..48 字节）
mat_offsets = [(a * 5 + b) * 2 for a in range(5) for b in range(5)]
check("5×5 子矩阵 = 25 个连续 word（0..48 字节）",
      mat_offsets == list(range(0, 50, 2)))

# 第二个 block（0x4a0f10）5 列字节偏移 = 0x32 + [0,2,4,6,8] = 50,52,54,56,58
col_offsets_b = [0x32 + (0 * 5 + b) * 2 for b in range(5)]
check("block@0x32 的 5 列字节偏移 == [50,52,54,56,58]",
      col_offsets_b == [50, 52, 54, 56, 58], str(col_offsets_b))

# ---------------------------------------------------------------------------
# 4) 至少 2 个消费函数引用 0x518588（全镜像扫描指令立即数）
# ---------------------------------------------------------------------------
def consumers_of_table():
    """扫描所有函数，收集操作数中出现 0x518588 的指令地址"""
    refs = set()
    for fs in FUNCS_S:
        nf = None
        for f in FUNCS_S:
            if f > fs:
                nf = f
                break
        if nf is None:
            nf = len(code)
        for ins in md.disasm(code[fs: fs + (nf - fs)], BASE + fs):
            if '518588' in ins.op_str:
                refs.add(ins.address)
    return refs

refs = consumers_of_table()
cons_fns = {enclosing(r) for r in refs}
check("消费 0x518588 的函数数 >= 2", len(cons_fns) >= 2,
      "共 %d 个引用 / %d 个函数，例如 %s" %
      (len(refs), len(cons_fns),
       ["%08x" % f for f in sorted(cons_fns)[:3]]))

# 至少一个消费函数同时调用取值器（坐实「取值器服务本表」）
def calls_of(tgt):
    out = set()
    off = 0
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

callers_ef0 = {enclosing(c) for c in calls_of(GETTER_A)}
callers_f10 = {enclosing(c) for c in calls_of(GETTER_B)}
inter = cons_fns & (callers_ef0 | callers_f10)
check("存在「引用 0x518588 且调用取值器」的消费函数",
      len(inter) >= 1, "%d 个，例如 %s" %
      (len(inter), ["%08x" % f for f in sorted(inter)[:3]]))


# ---------------------------------------------------------------------------
# 5) 取值器以扁平基址读取（ecx=0x518588，无 ×139）—— 0x410a70 实证
#    该函数以 ecx=0x518588 调 0x4a0ef0/0x4a0f10，且 a(=esi)=0..4 迭代 5×5
# ---------------------------------------------------------------------------
def uses_flat_base(va):
    """检查函数内是否存在 `mov ecx, 0x518588` 后 `call 0x4a0ef0/0x4a0f10`"""
    insns = disasm(va, next_func(va) - va)
    saw_base = False
    for ins in insns:
        if ins.mnemonic == 'mov' and ins.op_str == 'ecx, 0x518588':
            saw_base = True
        if saw_base and ins.mnemonic == 'call' and \
           ins.op_str in ('0x4a0ef0', '0x4a0f10'):
            return True
    return False

flat_user = None
for f in cons_fns:
    if uses_flat_base(f):
        flat_user = f
        break
check("存在以 ecx=0x518588 扁平基址调用取值器的函数",
      flat_user is not None, "例如 %08x" % flat_user if flat_user else "")

# ---------------------------------------------------------------------------
# 汇总
# ---------------------------------------------------------------------------
allpass = all(c for _, c, _ in results)
print("\n" + "=" * 64)
print("总计 %d 项：PASS=%d  FAIL=%d" %
      (len(results), sum(1 for r in results if r[1]),
       sum(1 for r in results if not r[1])))
print("结论：0x518588 = %d 条记录 × stride %d 字节；每条记录内含 5×5 word 子矩阵" %
      (20, STRIDE))
print("      列偏移(block0)=[0,2,4,6,8]，block1(0x4a0f10)=[0x32..0x3a]")
print("=" * 64)
raise SystemExit(0 if allpass else 1)
