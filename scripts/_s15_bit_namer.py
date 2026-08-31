# -*- coding: utf-8 -*-
"""
S15 未定名 bit（1/3/5/6/7/11）定名探针
对给定 handler，dump 函数体内全部 call，并对每个 callee 查 MSGX 锚点（一跳）。
用法: python scripts/_s15_bit_namer.py 0x408c20 0x40f850 ...
"""
import os, bisect, pickle, sys, json, collections
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

_d = pickle.load(open(os.path.join(HERE, "_insn_addrs.pkl"), "rb"))
FSTART = sorted(_d[1])          # 文件偏移
FSTART_VA = [x + BASE for x in FSTART]

MSGMAP = json.load(open(os.path.join(HERE, "msgx_id_map.json"), encoding="utf-8"))
TXT = json.load(open(os.path.join(HERE, "msgx_all_texts.json"), encoding="utf-8"))["texts"]
BYFUNC = collections.defaultdict(list)
for s in MSGMAP["sites"]:
    f = s["func"]
    f = f if isinstance(f, int) else int(f, 16)
    BYFUNC[f].append(s)


def hx(v):
    return v if isinstance(v, int) else int(v, 16)


def txt(i):
    for k in (str(i), "0x%x" % i):
        if k in TXT:
            return TXT[k]
    return "?"


def body(va):
    i = bisect.bisect_right(FSTART_VA, va) - 1
    end = FSTART_VA[i + 1] if i + 1 < len(FSTART_VA) else BASE + len(MEM)
    return va, min(end, va + 0x800)


def analyze(fva, depth=1, seen=None):
    if seen is None:
        seen = set()
    if fva in seen or depth < 0:
        return
    seen.add(fva)
    b0, b1 = body(fva)
    ins = list(md.disasm(MEM[b0 - BASE:b1 - BASE], b0))
    calls = []
    imms = []
    for it in ins:
        if it.mnemonic == "call" and it.op_str.startswith("0x"):
            calls.append(int(it.op_str, 16))
        for tok in it.op_str.replace(",", " ").split():
            if tok.startswith("0x") and len(tok) > 4:
                try:
                    v = int(tok, 16)
                    if 0x400000 < v < 0x600000:
                        continue
                    imms.append(v)
                except ValueError:
                    pass
    print("\n" + "=" * 76)
    print("fn 0x%06x  区间 0x%06x..0x%06x  (%d 条指令)" % (fva, b0, b1, len(ins)))
    # 自身 MSG
    own = BYFUNC.get(fva, [])
    if own:
        print("  -- 本体 MSGX (%d)" % len(own))
        for s in own:
            for i in s["ids"]:
                if isinstance(i, int):
                    print("     @0x%06x  0x%x [%d] %s" % (hx(s["at"]), i, i, txt(i)))
    # callee MSG
    for c in calls:
        ss = BYFUNC.get(c, [])
        if not ss:
            continue
        print("  -- callee 0x%06x MSGX (%d)" % (c, len(ss)))
        for s in ss[:8]:
            for i in s["ids"]:
                if isinstance(i, int):
                    print("     @0x%06x  0x%x [%d] %s" % (hx(s["at"]), i, i, txt(i)))
    # 常量
    cc = collections.Counter(imms)
    if cc:
        print("  -- 常量候选: " + ", ".join("0x%x" % k for k, _ in cc.most_common(14)))
    # 一跳下探
    if depth > 0:
        for c in calls:
            if c < 0x400000 or c > 0x600000:
                continue
            if c in (0x49f5e0, 0x49f5d0, 0x49f670, 0x49f830, 0x49f8f0, 0x49f9b0,
                     0x47b900, 0x47d910, 0x47da80, 0x4ebca0, 0x4ebcd0, 0x4ebd60,
                     0x49c390, 0x49c3d0, 0x49c410, 0x49c420, 0x49c440,
                     0x49c460, 0x49c4b0, 0x49c500, 0x49c520):
                continue
            if c in seen:
                continue
            analyze(c, depth - 1, seen)


if __name__ == "__main__":
    for a in sys.argv[1:]:
        analyze(int(a, 16), depth=1)
