# -*- coding: utf-8 -*-
"""S15 访问器类（0x49c390..0x49c520）全部调用点穷举 —— 定位 bit 的写入方。"""
import os, struct, bisect, pickle, collections
from capstone import *

HERE = os.path.dirname(os.path.abspath(__file__))
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)

API = {
    0x49c390: ("get_a(base,idx)", 1),
    0x49c3d0: ("get_b(base,idx)", 1),
    0x49c410: ("get_c(base,idx)", 1),
    0x49c420: ("set_prog(base,v5)", 1),
    0x49c440: ("set_hi3(base,v3)", 1),
    0x49c460: ("set_a(base,idx,val)", 2),
    0x49c4b0: ("set_b(base,idx,val)", 2),
    0x49c500: ("set_c(base,idx,val)", 2),
    0x49c520: ("get_a24_26(base)", 0),
}

_d = pickle.load(open(os.path.join(HERE, "_insn_addrs.pkl"), "rb"))
FSTART = sorted(_d[1])


def owner(va):
    r = va - BASE
    i = bisect.bisect_right(FSTART, r) - 1
    return (FSTART[i] + BASE) if i >= 0 else 0


def find_calls(target):
    out, i = [], 0
    while True:
        i = MEM.find(b"\xe8", i)
        if i < 0 or i + 5 > len(MEM):
            break
        rel = struct.unpack_from("<i", MEM, i + 1)[0]
        va = BASE + i
        if va + 5 + rel == target:
            out.append(va)
        i += 1
    return out


def back_args(callva, nargs, back=96):
    """回溯 call 前的 push 序列，返回 (arg1..argN)，arg1 = 最后压入"""
    st = max(BASE + 0x1000, callva - back)
    ins = list(md.disasm(MEM[st - BASE:callva - BASE], st))
    args = []
    for k in range(len(ins) - 1, -1, -1):
        it = ins[k]
        if it.mnemonic == "push":
            o = it.op_str
            if o.startswith("0x"):
                try:
                    args.append(int(o, 16)); continue
                except ValueError:
                    pass
            try:
                args.append(int(o))
            except ValueError:
                args.append(o)
            if len(args) == nargs:
                break
        elif it.mnemonic in ("call", "ret", "jmp", "jne", "je", "ja", "jbe", "jb", "jae"):
            if it.mnemonic == "call" and len(args) < nargs:
                break
            if it.mnemonic in ("ret", "jmp"):
                break
        elif it.mnemonic == "add" and it.op_str.startswith("esp"):
            break
    return args


rows = []
for tgt, (name, nargs) in API.items():
    for cva in find_calls(tgt):
        rows.append((tgt, name, cva, back_args(cva, nargs) if nargs else [], owner(cva)))

print("== 各访问器调用点计数 ==")
for tgt, (name, n) in sorted(API.items()):
    sub = [r for r in rows if r[0] == tgt]
    print(f"  0x{tgt:06x} {name:<22s} {len(sub)}")

print("\n== setter 调用点明细（按 API）==")
for tgt in (0x49c460, 0x49c4b0, 0x49c500, 0x49c420, 0x49c440):
    name = API[tgt][0]
    sub = sorted([r for r in rows if r[0] == tgt], key=lambda r: (str(r[3][0]) if r[3] else "", str(r[3][1]) if len(r[3]) > 1 else ""))
    print(f"\n-- 0x{tgt:06x} {name}  ({len(sub)} 处)")
    for _, _, cva, args, fn in sub:
        a = [("0x%x" % x if isinstance(x, int) else x) for x in args]
        print(f"    call@0x{cva:06x}  fn=0x{fn:06x}  args={a}")

print("\n== get_c / get_a24_26 调用点 ==")
for tgt in (0x49c410, 0x49c520):
    name = API[tgt][0]
    sub = [r for r in rows if r[0] == tgt]
    print(f"\n-- 0x{tgt:06x} {name}  ({len(sub)} 处)")
    for _, _, cva, args, fn in sub:
        a = [("0x%x" % x if isinstance(x, int) else x) for x in args]
        print(f"    call@0x{cva:06x}  fn=0x{fn:06x}  args={a}")

print("\n== bit 号 -> set_a/set_b 写入方 ==")
bitop = collections.defaultdict(lambda: collections.defaultdict(list))
for tgt, name, cva, args, fn in rows:
    if tgt not in (0x49c460, 0x49c4b0):
        continue
    if len(args) >= 2 and isinstance(args[0], int):
        bitop[args[0]][tgt].append((cva, fn, args[1]))
for b in sorted(bitop):
    for tgt in (0x49c460, 0x49c4b0):
        for cva, fn, val in bitop[b][tgt]:
            v = "0x%x" % val if isinstance(val, int) else val
            print(f"  bit {b:3d}  {'A' if tgt==0x49c460 else 'B'} := {v:<8s} @0x{cva:06x} fn=0x{fn:06x}")
