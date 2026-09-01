"""S5 (0x5197b0, 6×30B=180B) 字段访问谱：绝对地址 xref 聚合到 (field = off mod 30)。
目的：确认 +0x16/18/1a 除 setter 外是否存在绝对地址直写，并给出全部字段的读/写/位宽。
pickle 键 = 文件偏移；IMG[off:] @ VA = BASE+off
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

import pickle, struct
from collections import Counter, defaultdict
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x400000
IMG = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
d, starts = pickle.load(open(_ROOT + '/scripts/_insn_addrs.pkl', 'rb'))
SIZE = {off: s[0] for off, s in d.items()}
TEXT = {off: s[1] for off, s in d.items()}
STARTS = sorted(starts)
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False

S5 = 0x5197B0
NREC, STRIDE = 6, 30
SPAN = NREC * STRIDE  # 180

def find_insn_off(va):
    t = va - BASE
    for j in range(max(0, t - 16), t + 1):
        if j in SIZE and j <= t < j + SIZE[j]:
            return j
    return None

def fn_off_of(off):
    best = None
    for s in STARTS:
        if s <= off:
            if best is None or s > best: best = s
        else: break
    return best if best is not None else off

def width_of(t):
    if 'byte ptr' in t: return 'B'
    if 'word ptr' in t: return 'W'
    if 'dword ptr' in t: return 'D'
    return '?'

def dir_of(m, t):
    if m.startswith('mov'):
        parts = t.split(',')
        if len(parts) == 2:
            dst, src = parts[0].strip(), parts[1].strip()
            if 'ptr' in dst and 'ptr' not in src: return 'W'
            if 'ptr' in src and 'ptr' not in dst: return 'R'
        return '?'
    if m in ('test', 'cmp'): return 'T'
    if m in ('add', 'sub', 'or', 'and', 'xor'): return 'RW'
    if m in ('inc', 'dec'): return 'RW'
    return '?'

# 扫描 S5 全部 180 字节
recs = defaultdict(list)
for off in range(SPAN):
    va = S5 + off
    pat = struct.pack('<I', va)
    o = 0
    while True:
        i = IMG.find(pat, o)
        if i < 0: break
        o = i + 1
        hit = find_insn_off(BASE + i)
        if hit is None or hit not in SIZE: continue
        sz = SIZE[hit]
        b = list(md.disasm(IMG[hit: hit + sz + 16], BASE + hit))
        if not b: continue
        ins = b[0]
        m, t = ins.mnemonic, ins.op_str
        # 必须是内存操作数且以该地址作为位移
        if 'ptr' not in t: continue
        recs[off].append({
            'va': BASE + hit, 'fn': BASE + fn_off_of(hit),
            'txt': f'{m} {t}', 'w': width_of(t), 'dir': dir_of(m, t),
        })

print(f"S5 (0x{S5:06x}, {NREC}×{STRIDE}B) 绝对地址引用汇总")
print(f"{'off':>4} {'slot/field':>10} {'n':>4}  widths        dirs       样例")
for off in range(SPAN):
    r = recs.get(off, [])
    if not r: continue
    slot, field = off // STRIDE, off % STRIDE
    wc = Counter(x['w'] for x in r); dc = Counter(x['dir'] for x in r)
    ex = r[0]
    print(f"+{off:02x}  s{slot}f{field:<2d}  {len(r):>4}  {str(dict(wc)):<14}{str(dict(dc)):<12}0x{ex['va']:06x} {ex['txt']}")

print("\n===== 按字段(field = off mod 30) 聚合 =====")
byfield = defaultdict(list)
for off, r in recs.items():
    byfield[off % STRIDE].extend(r)
for f in sorted(byfield):
    r = byfield[f]
    wc = Counter(x['w'] for x in r); dc = Counter(x['dir'] for x in r)
    print(f"field +{f:02x}: n={len(r):>4}  widths={dict(wc)}  dirs={dict(dc)}")
    # 打印 cmp/test 的立即数（哨兵/阈值线索）
    for x in r:
        if x['txt'].startswith(('cmp', 'test')):
            print(f"      0x{x['va']:06x} {x['txt']}")
