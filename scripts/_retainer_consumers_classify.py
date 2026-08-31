#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续167(A): 定名 13 个 +0x2a 消费循环。
对 13 个 stride-47 循环中消费 word[entity+0x2a] 的函数做 capstone 反汇编（skipdata=True），
抽取特征向量，用于按「是否写候选池/是否读俸禄+0x28/是否读在城+0x25/是否调 MSG 显示/玩家/池构建器」自动打标。
纯静态，不改写任何文件。输出每个函数的特征表，供人工定名。
"""
import os, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x400000
MEM = open(os.path.join(os.path.dirname(__file__), "_unpacked_mem.bin"), "rb").read()
ERR = open(os.path.join(os.path.dirname(__file__), "_unpacked_mem.err.log"), "w", encoding="utf-8") if False else None

# 13 个 consumer（续167 列）
CONSUMERS = [
    0x45e3e0, 0x46a4a0, 0x47dce0, 0x47df00, 0x488100, 0x4a3920,
    0x4a5010, 0x4a5370, 0x4a6970, 0x4c0130, 0x4c9650, 0x4d7fe0,
]

# 已知 helper（用于定性打标）
ANCHORS = {
    0x49a7d0: "set_lord_idx(+0x2a 唯一 setter)",
    0x49a880: "inc_loyalty?",
    0x49ffc0: "affinity_score",
    0x49c460: "S15_set_a",
    0x49c4b0: "S15_set_b",
    0x49a990: "castle_rec_copy",
    0x47b900: "display_msg",
    0x4ebd60: "RNG",
    0x45e3e0: "build_cand_pool",
    0x49f5e0: "get_player",
    0x49f830: "get_slot",
    0x470690: "is_alive",
    0x47fc60: "sndata_fanout",
    0x49b960: "shared_setter_lib",
    0x49a5a0: "compat_setter",
}
POOL = 0x51e9c0

def disasm(va, n):
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.skipdata = True
    off = va - BASE
    return list(md.disasm(bytes(MEM[off:off + n]), va))

def feats(va):
    ins = disasm(va, 0x500)
    calls = []
    reads = set()
    pool_ref = 0
    push_ffff = 0
    for i in ins:
        m, op = i.mnemonic, i.op_str
        if m == "call" and op.startswith("0x"):
            try: calls.append(int(op, 16))
            except: pass
        # 放宽 +0x2a 检测：任何含 0x2a] / +2a] 的 operand（capstone 可能省 0x）
        low = op.lower().replace("0x", "")
        for offs in ("2a", "28", "25", "2c", "24", "29", "26", "22"):
            if offs + "]" in low and ("ptr" in op.lower()):
                reads.add(int(offs, 16))
        if "51e9c0" in low:
            pool_ref += 1
        if m == "push" and op.lower().endswith("ffff"):
            push_ffff += 1
    anc = sorted(set(calls) & set(ANCHORS))
    return {
        "n": len(ins), "reads": sorted(reads), "pool": pool_ref, "push_ffff": push_ffff,
        "calls": sorted(set(calls)), "anchors": anc,
    }

def main():
    print("=== 13 个 +0x2a 消费循环 · 锚点调用矩阵（capstone skipdata）===")
    for va in CONSUMERS:
        f = feats(va)
        al = " ".join("%s" % ANCHORS[a] for a in f["anchors"])
        r = " ".join("+0x%x" % r for r in f["reads"]) or "-"
        print("\n0x%06x  n=%d  reads[%s]  pool=%d  pushFFFF=%d" % (va, f["n"], r, f["pool"], f["push_ffff"]))
        print("  anchors: %s" % (al or "-"))
        # 打印与本主题相关的调用（去重）
        rel = [c for c in f["calls"] if c in ANCHORS]
        print("  anchor-calls: %s" % (" ".join("0x%x" % c for c in rel) or "-"))

if __name__ == "__main__":
    main()
