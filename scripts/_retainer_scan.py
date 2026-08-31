"""扫描所有「遍历武将实体」的循环（stride 0x2f=47 / 计数 0x172=370 / 基址 0x519868 系），
并报告它们对 word[entity+0x2a]（主君索引）与其它字段的消费方式。
"""
import pickle, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x400000
IMG = open('scripts/_unpacked_mem.bin', 'rb').read()
d, starts = pickle.load(open('scripts/_insn_addrs.pkl', 'rb'))
SIZE = {off: s[0] for off, s in d.items()}
TEXT = {off: s[1] for off, s in d.items()}
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False
STARTS = sorted(starts)

def fn_of(off):
    b = None
    for st in STARTS:
        if st <= off: b = st
        else: break
    return b if b is not None else off

def disasm_func_off(foff, maxlen=0x400):
    out = []; o = foff; end = foff + maxlen
    while o < end and o in SIZE:
        out.append((o, TEXT[o]))
        if TEXT[o] == 'ret': break
        o += SIZE[o]
    return out

# 1) 找 stride 47 (0x2f) 的步进指令
print("=" * 70)
print("(A) 实体遍历循环（stride 0x2f = 47）")
print("=" * 70)
loops = []
for off, s in d.items():
    t = s[1]
    if re.match(r'add (e?[a-z]x|e?[sd]i|e?bp), 0x2f$', t):
        loops.append(off)
print(f"共 {len(loops)} 处 `add reg, 0x2f`")
fns = {}
for off in loops:
    fn = fn_of(off)
    fns.setdefault(fn, []).append(off)
print(f"分布在 {len(fns)} 个函数\n")

# 2) 对每个函数，检查对 +0x2a 的消费
def uses(fn, pat):
    for o, t in disasm_func_off(fn):
        if re.search(pat, t):
            return (BASE + o, t)
    return None

print("=" * 70)
print("(B) 这些函数对 word[entity+0x2a]（主君索引）的消费")
print("=" * 70)
n_2a = 0
for fn in sorted(fns):
    # 取 +0x2a 的常见形式：esi-2 (base=entity+0x2c)、esi+0x2a、esi + 0x2a
    hit = uses(fn, r'\[e?(?:si|ax|bx|cx|dx|di|bp)(?: [+-] 0x2)?[ ]?\+?[ ]?0x2a\]')
    hit2 = uses(fn, r'\[e?[sd]i - 2\]')
    if hit or hit2:
        n_2a += 1
        print(f"  fn 0x{BASE+fn:06x}")
        if hit: print(f"      +0x2a 直接: 0x{hit[0]:06x}  {hit[1]}")
        if hit2: print(f"      [esi-2]:   0x{hit2[0]:06x}  {hit2[1]}  (= entity+0x2a 当 base=+0x2c)")
print(f"\n共 {n_2a} 个遍历函数消费 +0x2a")

# 3) 全镜像：所有读 word[..0x2a] 并与 0x172 / 0xffff 比较的点（主君索引判据）
print()
print("=" * 70)
print("(C) 全镜像：+0x2a 与哨兵 0x172(370) / 0xffff 的比较点")
print("=" * 70)
cnt = 0
for off, s in d.items():
    t = s[1]
    if ('0x2a]' in t) and ('0x172' in t or '0xffff' in t):
        print(f"  0x{BASE+off:06x} (fn 0x{BASE+fn_of(off):06x})  {t}")
        cnt += 1
        if cnt > 25: break
print(f"(共 {cnt}+ 处)")
