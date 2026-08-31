# -*- coding: utf-8 -*-
"""反汇编年龄计算区 0x49a560..0x49a660 + 找 BSDATA 生年字段 39 的消费方。"""
import re, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
mem = open(MEM, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

print("=" * 78)
print("A. 0x49a560 .. 0x49a660 线性反汇编")
print("=" * 78)
o = 0x49A560 - BASE
for ins in md.disasm(mem[o:o + 0x110], 0x49A560):
    print(f"  {ins.address:08x}  {ins.mnemonic:<8} {ins.op_str}")

print("\n" + "=" * 78)
print("B. 0x49a5d5 所属函数的 e8 调用方")
print("=" * 78)


def e8_callers(target):
    hits = []
    for i in range(len(mem) - 5):
        if mem[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", mem, i + 1)[0]
        if (BASE + i + 5 + rel) & 0xFFFFFFFF == target:
            hits.append(BASE + i)
    return hits


# 找函数起点: 向上找 55 8B EC 或 call 目标
def fn_start(addr, maxback=0x400):
    a = addr - BASE
    best = None
    for i in range(a, max(0, a - maxback), -1):
        if mem[i] == 0x55 and mem[i + 1] == 0x8B and mem[i + 2] == 0xEC:
            best = BASE + i
            break
    return best


fs = fn_start(0x49A5D5)
print(f"  0x49a5d5 所在函数起点: {fs:#010x}" if fs else "  未找到序言")
if fs:
    c = e8_callers(fs)
    print(f"  调用方 {len(c)} 处: {[hex(x) for x in c[:20]]}")
    print(f"\n  --- 该函数全文 ---")
    o = fs - BASE
    for ins in md.disasm(mem[o:o + 0x200], fs):
        print(f"  {ins.address:08x}  {ins.mnemonic:<8} {ins.op_str}")
        if ins.mnemonic == "ret":
            break

print("\n" + "=" * 78)
print("C. 全镜像搜 byte[reg+0x27] (=39, BSDATA 生年字段偏移)")
print("=" * 78)
for disp in ("0x27", "0x1b", "0x28", "0x29", "0x2b"):
    pats = [f"+ {disp}]"]
    n = 0
    for m in re.finditer(re.escape(f"+ {disp}]"), mem.decode("latin-1")):
        n += 1
    print(f"  ' + {disp}]' 字符串命中 {n} (仅文本计数, 忽略)")

# 用 capstone 扫
INS = []
o = 0
while o < len(mem) - 1:
    last = None
    for ins in md.disasm(mem[o:o + 4096], BASE + o):
        last = ins.address - BASE + ins.size
        INS.append((ins.address, ins.mnemonic, ins.op_str, ins.size))
    o = last if last and last > o else o + 4096
print(f"  收集指令 {len(INS)} 条")
GEN = {"eax", "ecx", "edx", "ebx", "esi", "edi"}
for disp in (0x27, 0x1B, 0x2B, 0x3A):
    hits = [(a, m, p) for a, m, p, s in INS
            if any(f"{r} + {hex(disp)}]" in p for r in GEN)]
    print(f"\n  byte/word [reg+{disp:#x}] 引用 {len(hits)} 处")
    for a, m, p in hits[:12]:
        print(f"    {a:08x}  {m:<8} {p}")
