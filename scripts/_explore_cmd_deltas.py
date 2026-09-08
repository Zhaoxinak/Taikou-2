# -*- coding: utf-8 -*-
# 探索脚本：反汇编 12 主命 handler，提取精确资源 delta 常量（非 *_ref.py，不进自测套件）
import os, struct
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 工程根
MEM = open(os.path.join(_ROOT, "scripts", "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

# (cmd_id, 名, handler) —— 主命 0..11 → code 2..13
HANDLERS = {
    0: ("贩卖军粮", 0x4AA100),
    1: ("购买军粮", 0x4AB2A0),
    2: ("军马",     0x4AA160),
    3: ("洋枪",     0x4AA1F0),
    4: ("开垦农田", 0x4AA290),
    5: ("改建",     0x4AA370),
    6: ("筑城",     0x4AB530),
    7: ("进贡",     0x4AB680),
    8: ("威吓",     0x4AB8F0),
    9: ("朝廷工作", 0x4AB3C0),
    10:("收集情报", None),
    11:("谋略",     0x4AA690),
}
# sat_add 包装器 → (字段偏移, cap)
WRAP = {0x4A32A0:(0x0C,100),0x4A32C0:(0x0D,250),0x4A3310:(0x0E,200),0x4A3360:(0x0F,100),
        0x4A33A0:(0x10,50000),0x4A33F0:(0x12,30000),0x4A3440:(0x14,30000),0x4A3530:(0x1A,200)}

# 实体 / 城表常用偏移名
OFFNAME = {0x0C:"农商",0x0D:"守城度",0x0E:"民心",0x0F:"生产率",0x10:"軍糧",
           0x12:"米",0x14:"資金",0x1A:"次级民情",0x09:"規模?",0x1B:"城種"}

def dis(va, n=0x300):
    return list(md.disasm(MEM[va-BASE:va-BASE+n], va))

for cid,(name,va) in HANDLERS.items():
    if va is None:
        print("\n=== cmd %d %s : (no handler / default no-op) ===" % (cid, name))
        continue
    print("\n=== cmd %d %s @0x%06X ===" % (cid, name, va))
    insns = dis(va)
    prev = None
    for ins in insns:
        s = ins.mnemonic + " " + ins.op_str
        mark = ""
        # 1) 调用 sat_add 包装器：标注字段 + cap
        if ins.mnemonic == "call":
            t = ins.operands[0].imm if ins.operands else 0
            if t in WRAP:
                off,cap = WRAP[t]
                pre = ("  前一条: "+prev) if prev else ""
                mark = "   <<SAT_WRAP 城+0x%02X(%s) cap=%d%s" % (off, OFFNAME.get(off,"?"), cap, pre)
        # 2) 写实体/城字段偏移（byte[esi+off] / word[esi+off]）
        else:
            for op in ins.operands:
                if op.type == 2:  # X86_OP_MEM
                    d = op.mem.disp
                    if d in OFFNAME:
                        mark = "   <<城+0x%02X(%s)" % (d&0xFF, OFFNAME[d&0xFF])
                    break
        print("  0x%06X: %-28s%s" % (ins.address, s, mark))
        prev = s
        if ins.mnemonic == "ret":
            break
