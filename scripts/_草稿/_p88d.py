# -*- coding: utf-8 -*-
"""_p88d.py — dump 0x4ab680 成功分支 + 0x4ebcd0 + 0x49fe40 精确调用链"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _dis_helper import disasm

def dump(va, n, label):
    print("==== %s @0x%x (%d bytes) ====" % (label, va, n))
    for r in disasm(va, n):
        print("  0x%x:\t%s\t%s" % (r["va"], r["mnem"], r["ops"]))
    print()

if __name__ == "__main__":
    # 0x4ab680 主函数
    dump(0x4ab680, 0x400, "0x4ab680 关系行动 dispatcher")
    # 0x4ebcd0 声称 sat_sub
    dump(0x4ebcd0, 0x40, "0x4ebcd0 (newrel?)")
    # 0x49fe40 set_diplomacy
    dump(0x49fe40, 0x80, "0x49fe40 set_diplomacy")
    # 0x4a33f0 城表 diplomacy +0x12c
    dump(0x4a33f0, 0x40, "0x4a33f0 城表 diplomacy")
