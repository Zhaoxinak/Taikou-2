# -*- coding: utf-8 -*-
"""找 byte[entity+0x16]（仕事コード|状態<<6）的写入点 —— 定位仕事割当菜单与名表。

用法: python3.7 _naisei_field16.py
"""
import sys
from collections import defaultdict
sys.path.insert(0, "scripts")
from _naisei_scan import MEM, BASE, disas_fn, caller_func

from _ins_index import build_index

idx = build_index(verbose=False)
ins_at = idx.ins_at
addrs = sorted(ins_at)

ENT = 0x519868


def enclosing(va):
    import bisect
    i = bisect.bisect_right(addrs, va) - 1
    return addrs[max(0, i)]


def scan():
    hits = []
    for va in addrs:
        ins = ins_at[va]
        if ins.mnemonic not in ("mov", "or", "and", "add", "sub", "xor", "shl", "shr"):
            continue
        # 只看 byte 写
        ops = ins.operands
        if len(ops) != 2:
            continue
        dst = ops[0]
        if dst.type != 3:  # mem
            continue
        if dst.mem.disp != 0x16 or dst.size not in (1, 0):
            continue
        if ins.mnemonic not in ("mov", "or", "and", "xor", "add", "sub"):
            continue
        # 排除读（mov reg, [..]）
        if ops[1].type == 3:
            continue
        hits.append(ins)
    return hits


def main():
    hits = scan()
    print("byte[..+0x16] 写入点: %d" % len(hits))
    fns = defaultdict(list)
    for ins in hits:
        fns[caller_func(ins.address)].append(ins)
    for fn in sorted(fns):
        body = disas_fn(fn, maxlen=0x3000, stop_ret=False)
        txt = "\n".join(i.op_str for i in body)
        tags = []
        if "0x519868" in txt:
            tags.append("ENT")
        if "0x51eb88" in txt:
            tags.append("CASTLE")
        if "0x5179b8" in txt:
            tags.append("PROV14")
        if "0x519548" in txt:
            tags.append("PROV5")
        print("0x%06x  n=%d  %s   sites=%s" % (
            fn, len(fns[fn]), ",".join(tags),
            " ".join("0x%06x" % i.address for i in fns[fn])))


if __name__ == "__main__":
    main()
