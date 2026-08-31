# -*- coding: utf-8 -*-
"""扫描 0x49c520(A24..A26) / 0x49c530(A27,A28) 全部调用点，dump 返回值(al)消费上下文。"""
import os, sys, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("bl", os.path.join(HERE, "_s15_bit_locate.py"))
bl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bl)
MEM = bl.MEM; md = bl.md; BASE = bl.BASE

for TGT in (0x49c520, 0x49c530):
    print("\n########## 访问器 0x%06x 调用点 ##########" % TGT)
    i = 0; n = 0
    while True:
        i = MEM.find(b"\xe8", i)
        if i < 0:
            break
        rel = int.from_bytes(MEM[i + 1:i + 5], "little", signed=True)
        va = BASE + i
        if va + 5 + rel == TGT:
            n += 1
            ac = list(md.disasm(MEM[va - BASE:va - BASE + 0x50], va))
            fn = bl.fn_of(va)
            print("\n  call@0x%06x  fn=0x%06x" % (va, fn))
            for it in ac:
                m = "  <<<" if it.address == va else ""
                print("     0x%06x  %s %s%s" % (it.address, it.mnemonic, it.op_str, m))
        i += 1
    print("  (共 %d 处)" % n)
