# -*- coding: utf-8 -*-
"""解码属性 getter 0x4c7c30 的 20 项跳表 0x4c7e84, 逐分支还原字段。"""
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
mem = open(MEM_PATH, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

TBL = 0x4C7E84
N = 20
print("=" * 78)
print(f"跳表 {TBL:#x} 共 {N} 项")
print("=" * 78)
tbl = []
for i in range(N):
    va, = struct.unpack_from("<I", mem, TBL - BASE + 4 * i)
    tbl.append(va)
    print(f"  [{i:2}] {va:#010x}")

SKILLS = ["口才", "马术", "算术", "剑术", "忍术", "兵法", "洋枪", "筑城", "礼法", "茶道"]


def branch_body(va):
    """从 va 起取到跳转/ret 为止的指令串。"""
    o = va - BASE
    out = []
    for ins in md.disasm(mem[o:o + 60], va):
        out.append((ins.address, ins.mnemonic, ins.op_str))
        if ins.mnemonic in ("ret", "jmp") or len(out) > 8:
            break
    return out


print("\n" + "=" * 78)
print("各分支体")
print("=" * 78)
for i, va in enumerate(tbl):
    print(f"\n--- 属性 {i:2} -> {va:#010x} ---")
    for a, m, o in branch_body(va):
        print(f"    {a:08x}  {m:<8} {o}")

print("\n" + "=" * 78)
print("语义推断 (ecx = 武将实体指针)")
print("=" * 78)
# 规则: byte[+0xf]&3 -> 技能0; >>2&3 -> 技能1; >>4&3 -> 技能2; >>6&3 -> 技能3
#       byte[+0x10] 同理 -> 技能4..7; byte[+0x11] -> 技能8,9
#       byte[+0xb]/[+0xc]/[+0xd]/[+0xe] -> 能力
ABILITY = {0xB: "能力@+0xb", 0xC: "能力@+0xc", 0xD: "外交", 0xE: "魅力"}
for i, va in enumerate(tbl):
    body = " ; ".join(f"{m} {o}" for a, m, o in branch_body(va))
    # 抽 off/shift
    offs = []
    for a, m, o in branch_body(va):
        if "0xf]" in o or "0x10]" in o or "0x11]" in o or "+ 0xb]" in o or "+ 0xc]" in o or "+ 0xd]" in o or "+ 0xe]" in o:
            offs.append(o)
    print(f"  [{i:2}] {body[:110]}")
