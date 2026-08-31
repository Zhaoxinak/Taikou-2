# -*- coding: utf-8 -*-
"""
扫描 get_c(0x49c410) 全部调用点，提取 idx=[esp+4]，并 dump 调用后 ~0x40 字节的反汇编，
看返回值(al)如何被消费（cmp/mov/算术），以定语义。
"""
import os, bisect, pickle, sys, json, collections, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("bl", os.path.join(HERE, "_s15_bit_locate.py"))
bl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bl)

MEM = bl.MEM
md = bl.md
BASE = bl.BASE
FSTART_VA = bl.FSTART_VA
fn_of = bl.fn_of
BYFUNC = bl.BYFUNC
txt = bl.txt

GET_C = 0x49c410


def idx_before(call_va, span=0x40):
    off = call_va - BASE - span
    off = max(off, 0)
    ins = list(md.disasm(MEM[off:off + span + 0x10], BASE + off))
    pushes = []
    for it in ins:
        if it.address >= call_va:
            break
        if it.mnemonic == "push":
            pushes.append((it.address, it.op_str))
    last = pushes[-1] if pushes else None
    if last is None:
        return None, []
    op = last[1].strip()
    try:
        idx = int(op, 16) if op.startswith("0x") else int(op)
    except ValueError:
        idx = ("reg", op)
    return idx, ins


def after_ctx(call_va, n=0x48):
    off = call_va - BASE
    ins = list(md.disasm(MEM[off:off + n], call_va))
    return ins


def main():
    rows = []
    i = 0
    while True:
        i = MEM.find(b"\xe8", i)
        if i < 0:
            break
        rel = int.from_bytes(MEM[i + 1:i + 5], "little", signed=True)
        va = BASE + i
        tgt = va + 5 + rel
        if tgt == GET_C:
            idx, insb = idx_before(va)
            fn = fn_of(va)
            rows.append((idx, va, fn))
        i += 1

    print("== get_c(0x49c410) 调用点 %d 处 ==" % len(rows))
    byidx = collections.defaultdict(list)
    for idx, va, fn in rows:
        key = idx if isinstance(idx, int) else str(idx)
        byidx[key].append((va, fn))

    for key in sorted(byidx, key=lambda k: (isinstance(k, str), str(k))):
        items = byidx[key]
        print("\n########## 段C 索引 %s 读取 : %d 处 ##########" % (key, len(items)))
        for va, fn in items:
            print("\n  -- get_c idx=%s  call@0x%06x  fn=0x%06x --" % (key, va, fn))
            ac = after_ctx(va, 0x50)
            for it in ac:
                mark = "  <<<" if it.address == va else ""
                print("     0x%06x  %s %s%s" % (it.address, it.mnemonic, it.op_str, mark))
    return byidx


if __name__ == "__main__":
    main()
