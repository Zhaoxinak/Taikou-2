"""枚举饱和加 0x4ebca0 / 饱和减 0x4ebcd0 的调用方与前导 push 参数。"""
import pickle
BASE = 0x400000
d, starts = pickle.load(open('scripts/_insn_addrs.pkl', 'rb'))
SIZE = {off: s[0] for off, s in d.items()}
TEXT = {off: s[1] for off, s in d.items()}

def fn_of(off):
    b = None
    for st in sorted(starts):
        if st <= off: b = st
        else: break
    return b if b is not None else off

def args_before(off, n=6, win=0x40):
    """向前收集最近的 push（返回正序：最后 push 的在最后）。遇 gap/call 停。"""
    o = off; out = []
    lo = off - win
    while o > lo and len(out) < n:
        o -= SIZE.get(o, 1)
        if o not in SIZE:
            break
        t = TEXT[o]
        if t.startswith('push '):
            out.append(t)
        elif t.startswith('call '):
            break
    return out[::-1]

for target, label in ((0x4ebca0, '饱和加 min(a+b,cap)'), (0x4ebcd0, '饱和减 (a>b)?a-b:0')):
    tgt = f'call 0x{target:x}'
    sites = [(off, fn_of(off)) for off, s in d.items() if s[1] == tgt]
    print(f"=== {label} 0x{target:06x}: {len(sites)} 个调用点 ===")
    for off, fn in sorted(sites):
        print(f"  0x{BASE+off:06x} (fn 0x{BASE+fn:06x})  pushes={args_before(off)}")
    # 统计 cap 常量
    from collections import Counter
    caps = Counter()
    for off, fn in sites:
        for p in args_before(off):
            if p.startswith('push 0x'):
                caps[p] += 1
    print(f"  --- push 常量统计: {dict(caps)}")
    print()
