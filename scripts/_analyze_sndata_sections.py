#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SNDATA 分段字节消费分析 (Task #22):
  读原语 (文件读取):
    0x47da10  -> 读 1 字节 (al)
    0x47da50  -> 读 1 字 (ax, 2 字节)
    0x47d910  -> 读 1 字节写到 *dest   (内部 call 0x47da10)
    0x47d930  -> 读 1 字写到 *dest      (内部 call 0x47da50)
  每个 sub-loader 内统计这些调用次数 -> 直接(非循环)读取字节数。
  再检测循环 (jne 回边 + ecx 计数) 估算倍增。
"""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BASE = 0x400000
data = open(r"scripts/_unpacked_mem.bin","rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

SUBS = [0x47dae0,0x47dce0,0x47e130,0x47e3a0,0x47e440,0x47e5a0,0x47e770,
        0x47ea80,0x47ebb0,0x47ecb0,0x47ed10,0x47ed70,0x47ee50,0x47ef00,
        0x47f050,0x47f0a0,0x47f1b0,0x47f210]
READ1 = {0x47da10, 0x47d910}   # 1 byte
READ2 = {0x47da50, 0x47d930}   # 2 bytes

def analyze(addr):
    chunk = data[addr-BASE:addr-BASE+0x800]
    insns = list(md.disasm(chunk, addr))
    n1 = n2 = 0
    loopbacks = []
    last_ea = None
    for ins in insns:
        if ins.mnemonic == "call":
            t = int(ins.op_str.replace("0x",""),16) if ins.op_str.startswith("0x") else None
            if t in READ1: n1 += 1
            elif t in READ2: n2 += 1
        if ins.mnemonic in ("jne","je","jmp","loop") and ins.op_str.startswith("0x"):
            target = int(ins.op_str,16)
            if target < ins.address:
                loopbacks.append((ins.address, target))
        if ins.mnemonic == "ret":
            break
    # 估算循环倍增: 若循环体内含 read, 且计数器来自常数 -> 粗略记下来
    return n1, n2, loopbacks, len(insns)

print("# SNDATA 各 sub-loader 文件读取调用计数")
tot1 = tot2 = 0
for a in SUBS:
    n1, n2, loops, nins = analyze(a)
    bytes_direct = n1 + 2*n2
    tot1 += n1; tot2 += n2
    # 检测循环计数: 找 mov ecx, 0xNNN 且后面有 jne 回边
    loopinfo = f"{len(loops)} loops" if loops else "-"
    print(f"@0x{a:08x}  read1B(x{n1}) read2B(x{n2}) -> direct {bytes_direct} B | {loopinfo} | insns={nins}")
print(f"\n合计 direct: 1B-calls={tot1} 2B-calls={tot2} -> {tot1+2*tot2} bytes (不含循环倍增)")
print("DONE")
