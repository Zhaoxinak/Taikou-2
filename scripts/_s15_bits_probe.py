# -*- coding: utf-8 -*-
"""
S15 bitset 测试器调用点穷举探针（承接续148 下一步A）
扫全镜像 call 0x49c390 / 0x49c3d0，回溯 push 实参，建 bit 号分布表。
"""
import os, struct, bisect, pickle, collections
from capstone import *
from capstone.x86 import *

HERE = os.path.dirname(os.path.abspath(__file__))
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

TARGETS = {0x49c390: "A(+2)", 0x49c3d0: "B(+0xa)"}


def find_calls(target):
    """全镜像搜 e8 rel32 -> target"""
    out = []
    i = 0
    n = len(MEM)
    while True:
        i = MEM.find(b"\xe8", i)
        if i < 0 or i + 5 > n:
            break
        rel = struct.unpack_from("<i", MEM, i + 1)[0]
        va = BASE + i
        dst = va + 5 + rel
        if dst == tgt:
            out.append(va)
        i += 1
    return out


def disasm_at(va, nbytes):
    off = va - BASE
    return list(md.disasm(MEM[off:off + nbytes], va))


def back_scan_push(callva, back=64):
    """在 call 之前 back 字节内反汇编，找最后一条 push 立即数/寄存器"""
    st = max(BASE + 0x1000, callva - back)
    ins = disasm_at(st, callva - st)
    res = {"imm": None, "reg": None, "pre": []}
    for k in range(len(ins) - 1, -1, -1):
        it = ins[k]
        res["pre"].append((it.address, it.mnemonic, it.op_str))
        if res["imm"] is None and it.mnemonic == "push":
            o = it.op_str
            if o.startswith("0x"):
                try:
                    res["imm"] = int(o, 16)
                    res["pushva"] = it.address
                    continue
                except ValueError:
                    pass
            try:
                v = int(o)
                res["imm"] = v
                res["pushva"] = it.address
                continue
            except ValueError:
                res["reg"] = o
                res["pushva"] = it.address
    return res


def func_of(va, fstart):
    i = bisect.bisect_right(fstart, va) - 1
    r = va - BASE
    i = bisect.bisect_right(fstart, r) - 1
    return (fstart[i] + BASE) if i >= 0 else None


_d = pickle.load(open(os.path.join(HERE, "_insn_addrs.pkl"), "rb"))
IMAP = _d[0]
FSTART = sorted(_d[1])

rows = []
for tgt, tag in TARGETS.items():
    for cva in find_calls(tgt):
        r = back_scan_push(cva)
        rows.append((tgt, tag, cva, r.get("imm"), r.get("reg"), r.get("pushva")))

print("== 调用点总数 ==")
for tgt, tag in TARGETS.items():
    print(f"  0x{tgt:06x} [{tag}] : {sum(1 for r in rows if r[0]==tgt)}")

print("\n== 按 bit 号分布（立即数实参）==")
for tgt, tag in TARGETS.items():
    c = collections.Counter(r[3] for r in rows if r[0] == tgt and r[3] is not None)
    print(f"-- 0x{tgt:06x} [{tag}] 立即数实参 {sum(c.values())} 条, distinct {len(c)}")
    for k in sorted(c):
        print(f"     bit {k:3d} (0x{k:02x}) x{c[k]}")

print("\n== 寄存器实参（非立即数）==")
for tgt, tag in TARGETS.items():
    sub = [r for r in rows if r[0] == tgt and r[3] is None]
    print(f"-- 0x{tgt:06x} [{tag}] {len(sub)} 条")
    for r in sub:
        pv = r[5] if r[5] is not None else 0
        print(f"     0x{r[2]:06x}  push {r[4]}   (push@0x{pv:06x})")

print("\n== 逐条明细（含所在函数，按 bit 排序）==")
for tgt, tag in TARGETS.items():
    print(f"\n-- 0x{tgt:06x} [{tag}]")
    for r in sorted([x for x in rows if x[0] == tgt], key=lambda x: (x[3] is None, x[3])):
        fn = func_of(r[2], FSTART)
        pv = r[5] if r[5] is not None else 0
        print(f"  bit={r[3]}  call@0x{r[2]:06x}  fn=0x{fn:06x}  push@0x{pv:06x} reg={r[4]}")

# 配对分析：A/B 是否成对出现（bit 相同、函数相同）
print("\n== A/B 配对分析 ==")
A = {(func_of(r[2], FSTART), r[3]): r[2] for r in rows if r[0] == 0x49c390 and r[3] is not None}
B = {(func_of(r[2], FSTART), r[3]): r[2] for r in rows if r[0] == 0x49c3d0 and r[3] is not None}
print(f"  A 键 {len(A)}  B 键 {len(B)}  交集 {len(set(A) & set(B))}")
onlyA = sorted(set(A) - set(B))
onlyB = sorted(set(B) - set(A))
print(f"  仅 A（无 ¬B 检查）: {[(f'0x{f:06x}', b) for f, b in onlyA]}")
print(f"  仅 B: {[(f'0x{f:06x}', b) for f, b in onlyB]}")

# 每个 bit 被哪些函数测试
print("\n== bit -> 函数 映射 ==")
bitfn = collections.defaultdict(set)
for r in rows:
    if r[3] is not None:
        bitfn[r[3]].add(func_of(r[2], FSTART))
for b in sorted(bitfn):
    fns = sorted(x for x in bitfn[b] if x)
    print(f"  bit {b:3d}: {len(fns)} 函数 -> {['0x%06x' % f for f in fns]}")

# 段 C 测试器搜索：byte[reg + 0x13] 形态
print("\n== 段 C 候选：全镜像 byte ptr [reg + 0x13] / [reg+0x13] 访问 ==")
pat_hits = collections.Counter()
for va in sorted(IMAP):
    off = va - BASE
    ins = list(md.disasm(MEM[off:off + 12], va))
    if not ins:
        continue
    it = ins[0]
    if "+0x13" in it.op_str and "[" in it.op_str and "byte" in it.op_str:
        pat_hits[it.op_str] += 1
for k, v in pat_hits.most_common(40):
    print(f"   {v:4d}  {k}")
