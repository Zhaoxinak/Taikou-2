# -*- coding: utf-8 -*-
"""城表 0x51eb88（31B × 200）字段访问面穷举。

三类命中：
  A. 立即数落在 [0x51eb88, 0x51eb88+200*31)（含 base±1..±4）
  B. 字面 0x51eb88 / ÷31 魔数 0x84210843
  C. 引用了上述任一的函数体内，寄存器相对访问的位移（按 [reg+disp] 收集）
输出：offset -> {width: count, R/W}，按函数分组。
"""
import bisect, pickle
from collections import Counter, defaultdict

BASE = 0x400000
d = pickle.load(open(r"scripts/_insn_addrs.pkl", "rb"))
IMAP = d[0]
FSTART = sorted(d[1])
RVAS = sorted(IMAP)

def owner(rva):
    i = bisect.bisect_right(FSTART, rva) - 1
    return FSTART[i] if i >= 0 else FSTART[0]

def fend(rva):
    i = bisect.bisect_right(FSTART, rva) - 1
    return FSTART[i + 1] if i + 1 < len(FSTART) else max(IMAP) + 1

TBL = 0x51EB88
STRIDE = 31
N = 200
END = TBL + N * STRIDE          # 0x5203c0
MAGIC31 = "0x84210843"

# ---- A/B：直接引用 ----
region = set(range(TBL - 4, END + 4))
lit_hits = []
magic_hits = []
for r in RVAS:
    t = IMAP[r][1]
    if TBL == 0x51EB88 and "0x51eb88" in t:
        lit_hits.append(r)
    if MAGIC31 in t:
        magic_hits.append(r)
    else:
        for tok in t.replace(",", " ").split():
            if tok.startswith("0x") and len(tok) == 8:
                try:
                    imm = int(tok, 16)
                except Exception:
                    continue
                if TBL - 4 <= imm < END + 4:
                    lit_hits.append(r)
                    break

print("=== 直接引用 0x51eb88 区域（含 ±4）的指令 ===")
print("count:", len(lit_hits))
fs = Counter(owner(r) + BASE for r in lit_hits)
for f, n in fs.most_common():
    print(f"  0x{f:06x}  x{n}")
print()
print("=== ÷31 魔数 0x84210843 出现处 ===")
print("count:", len(magic_hits))
for r in magic_hits:
    print(f"  0x{r+BASE:06x}  f=0x{owner(r)+BASE:06x}  {IMAP[r][1]}")
print()

# ---- C：这些函数体内的寄存器相对访问位移 ----
target_funcs = sorted(set(owner(r) for r in lit_hits) | set(owner(r) for r in magic_hits))
print(f"=== 涉表函数 {len(target_funcs)} 个：寄存器相对位移统计 ===")
import re
DISP = re.compile(r"\[(e[a-z]{2}|d[il]|a[lx]|b[lx]|c[xl]|s[il]|b[ppl])?(?:\s*\+\s*([0-9a-fx]+))?\]")

field = defaultdict(Counter)     # disp -> Counter("R"/"W")
disp_by_func = defaultdict(Counter)
for f in target_funcs:
    e = min(fend(f), f + 0x800)
    for r in RVAS[bisect.bisect_left(RVAS, f):bisect.bisect_left(RVAS, e)]:
        t = IMAP[r][1]
        if "[" not in t:
            continue
        # 只看 [reg + disp]（disp 为 0x.. 或小常数）
        m = re.search(r"\[(\w+)(?:\s*\+\s*(0x[0-9a-f]+|\d+))?\]", t)
        if not m:
            continue
        reg, disp_s = m.group(1), m.group(2)
        if reg in ("esp", "ebp"):
            continue
        if disp_s is None:
            continue
        disp = int(disp_s, 16) if disp_s.startswith("0x") else int(disp_s)
        if disp == 0 or disp >= 0x40:
            continue
        # 读/写
        if "]," in t[t.find("["):]:
            pass
        # 判断内存操作数在 '#' 左还是右
        i = t.find("[")
        j = t.find("]", i)
        rest = t[j + 1:].lstrip()
        is_w = rest.startswith(",")
        kind = "W" if is_w else "R"
        width = "byte" if "byte ptr" in t else ("word" if "word ptr" in t else ("dword" if "dword ptr" in t else "?"))
        field[disp][f"{width}:{kind}"] += 1
        disp_by_func[f + BASE][disp] += 1

print("disp : byte/word/dword × R/W 计数（按 disp 排序）")
for disp in sorted(field):
    if disp >= 0x20:
        continue
    item = field[disp]
    tot = sum(item.values())
    print(f"  +0x{disp:02x} ({disp:2d})  n={tot:3d}   " +
          "  ".join(f"{k}={v}" for k, v in item.most_common()))

print()
print("=== 高位移（0x20..0x3f，可能是别的结构）===")
for disp in sorted(field):
    if 0x20 <= disp < 0x40:
        print(f"  +0x{disp:02x}  {dict(field[disp])}")
