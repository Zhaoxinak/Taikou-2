# -*- coding: utf-8 -*-
"""定位实体五维块: 找连续写 +0xa..+0xe 的站点 / 5 次循环拷贝。"""
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>

import re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
mem = open(MEM_PATH, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)

print("=" * 78)
print("A. 同一函数内同时写 byte[reg+0xb] 与 [reg+0xc] 与 [reg+0xd] 与 [reg+0xe]")
print("=" * 78)
o = 0
writes = {d: [] for d in range(0xA, 0x12)}
while o < len(mem) - 1:
    last = None
    for ins in md.disasm(mem[o:o + 4096], BASE + o):
        last = ins.address - BASE + ins.size
        ops = ins.op_str
        if ins.mnemonic != "mov" or "byte ptr" not in ops:
            continue
        m = re.match(r"byte ptr \[(\w+) \+ (0x[0-9a-f]+)\], (\w+)$", ops.split(",", 1)[1].strip()) \
            if "," in ops else None
        if not m:
            continue
        reg, d, src = m.group(1), int(m.group(2), 16), m.group(3)
        if reg in {"eax", "ecx", "edx", "ebx", "esi", "edi"} and d in writes:
            writes[d].append(ins.address)
    o = last if last and last > o else o + 4096

for d, v in writes.items():
    print(f"  byte[+0x{d:x}] 写入 {len(v)} 处  例 {[hex(x) for x in v[:5]]}")

# 找 +0xb..+0xe 写入地址接近(同函数 0x80 内)的
print("\n  --- +0xb 写入点附近 0x60 内是否也有 +0xc/+0xd/+0xe 写 ---")
sb, sc, sd, se = set(writes[0xB]), set(writes[0xC]), set(writes[0xD]), set(writes[0xE])
for a in sorted(sb)[:400]:
    near = lambda S: any(abs(x - a) < 0x70 for x in S)
    if near(sc) and near(sd) and near(se):
        print(f"    {a:#010x} 附近同时有 +0xc/{near(sc)} +0xd/{near(sd)} +0xe/{near(se)}")

print("\n" + "=" * 78)
print("B. 反汇编最像五维拷贝的站点 (前 3 个)")
print("=" * 78)
cands = []
for a in sorted(sb):
    near = lambda S: any(abs(x - a) < 0x70 for x in S)
    if near(sc) and near(sd) and near(se):
        cands.append(a)
for a in cands[:3]:
    o2 = max(0, a - BASE - 48)
    print(f"\n--- 站点 {a:#010x} 上下文 ---")
    for ins in md.disasm(mem[o2:o2 + 160], BASE + o2):
        print(f"  {ins.address:08x}  {ins.mnemonic:<8} {ins.op_str}")
        if ins.address > a + 0x50:
            break
