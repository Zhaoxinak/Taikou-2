# -*- coding: utf-8 -*-
"""全镜像扫描 word[entity+0x2a]（主君索引）的读写点 + 定位 0x4a6970 同族函数族。

复用 scripts/_insn_addrs.pkl（d[0]={rva:(size,"mnem op")}，d[1]=函数起点 rva 列表）。
命中三类：
  A. 寄存器相对 word，位移 = +0x2a 或 -2（esi=base+0x2c 惯用法）
  B. 绝对立即数 ∈ {0x519892+i*47}（entity[i]+0x2a）
  C. 字面 0x519892 / 迭代基点 0x519894(=[esi-2] 起的 +0x2c 基点)
同族判据：函数体内含 add reg,0x2f(47) / /47 魔数 0xae4c415d / 计数 370(0x172) /
          字面 0x519868 / 迭代基点 0x519894
"""
import bisect, pickle

BASE = 0x400000
d = pickle.load(open(r"scripts/_insn_addrs.pkl", "rb"))
IMAP = d[0]                      # rva -> (size, text)
fstarts = sorted(d[1])           # 函数起点 rva 列表
print("insns:", len(IMAP), "funcs:", len(fstarts))

def owner(rva):
    i = bisect.bisect_right(fstarts, rva) - 1
    return fstarts[i] if i >= 0 else fstarts[0]

def fend(rva):
    i = bisect.bisect_right(fstarts, rva) - 1
    return fstarts[i + 1] if i + 1 < len(fstarts) else max(IMAP) + 1

RVAS = sorted(IMAP)

ENT_BASE = 0x519868
STRIDE = 47
N_ENT = 370
abs_2a = set((ENT_BASE + 0x2a + i * STRIDE) - BASE for i in range(N_ENT))
abs_2c = set((ENT_BASE + 0x2c + i * STRIDE) - BASE for i in range(N_ENT))

hits = []  # (rva, func, kind, text)
for rva in RVAS:
    size, txt = IMAP[rva]
    kinds = []
    op = txt.split(" ", 1)[1] if " " in txt else ""
    # A. 寄存器相对
    if "word ptr" in op and ("+ 0x2a]" in op or "- 2]" in op or "+0x2a]" in op):
        kinds.append("reg-rel word +0x2a/-2")
    # B/C. 立即数
    for tok in op.replace(",", " ").split():
        if tok.startswith("0x"):
            try:
                imm = int(tok, 16)
            except Exception:
                continue
            if imm in abs_2a:
                kinds.append("ABS entity[i]+0x2a")
            elif imm in abs_2c:
                kinds.append("ABS iter-base +0x2c")
            elif imm == 0x519892:
                kinds.append("lit 0x519892")
            elif imm == 0x519894:
                kinds.append("iter-base 0x519894")
    if kinds:
        hits.append((rva, owner(rva), ";".join(sorted(set(kinds))), txt))

print("raw hits:", len(hits))

fam = {}
for (rva, f, k, t) in hits:
    fam.setdefault(f, []).append((rva, k, t))

feat_of = {}
for f in fam:
    e = min(fend(f), f + 0x800)
    feats = []
    for rva in RVAS[bisect.bisect_left(RVAS, f):bisect.bisect_left(RVAS, e)]:
        t = IMAP[rva][1]
        if t.startswith("add ") and ("0x2f" in t or ", 47" in t):
            feats.append("stride47")
        elif "0xae4c415d" in t:
            feats.append("/47magic")
        elif "0x172" in t or ", 370" in t:
            feats.append("cnt370")
        elif "0x519868" in t:
            feats.append("base519868")
    feat_of[f] = sorted(set(feats))

print()
print("=== 命中函数汇总（按特征数降序）===")
for f in sorted(fam, key=lambda x: -len(feat_of[x])):
    print(f"  0x{f+BASE:06x}  n_hits={len(fam[f]):3d}  feat={feat_of[f]}")

print()
print("=== 明细：+0x2a 相关指令 ±5 条上下文 ===")
for f in sorted(fam, key=lambda x: -len(feat_of[x])):
    e = min(fend(f), f + 0x800)
    body = RVAS[bisect.bisect_left(RVAS, f):bisect.bisect_left(RVAS, e)]
    idx = {r: i for i, r in enumerate(body)}
    print(f"\n----- func 0x{f+BASE:06x} .. 0x{e+BASE:06x}  feat={feat_of[f]} -----")
    shown = set()
    for (rva, k, t) in fam[f]:
        i = idx.get(rva)
        if i is None:
            continue
        for j in range(max(0, i - 5), min(len(body), i + 6)):
            if j in shown:
                continue
            shown.add(j)
            r = body[j]
            mark = "   <<<< HIT" if r == rva else ""
            print(f"  0x{r+BASE:06x}  {IMAP[r][1]}{mark}")
        print("  " + "-" * 46)
