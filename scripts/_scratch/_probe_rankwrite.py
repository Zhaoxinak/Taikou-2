# -*- coding: utf-8 -*-
"""找 rank 写回指令 (and byte[reg+0x2d], 0xf8) 与其所属函数；并扫描 merit 阈值表。"""
import struct, os, bisect

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
mem = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
N = len(mem)

# 函数头集合
tg = set()
i = 0
while True:
    i = mem.find(b"\xe8", i)
    if i < 0:
        break
    rel = struct.unpack_from("<i", mem, i + 1)[0]
    t = (i + BASE) + 5 + rel
    if 0x401000 <= t < 0x4f0000:
        tg.add(t)
    i += 1
funcs = sorted(tg)
def host(va):
    k = bisect.bisect_right(funcs, va) - 1
    return funcs[k] if k >= 0 else 0

out = []

# 搜 and byte[reg+0x2d], 0xf8 ：编码 80 6x 2d f8（x=0..7，reg_op AND=4 => 0x60|rm）
sigs = [bytes([0x80, 0x60 | r, 0x2d, 0xf8]) for r in (0,1,2,3,5,6,7)]
hits = []
for sig in sigs:
    i2 = 0
    while True:
        i2 = mem.find(sig, i2)
        if i2 < 0:
            break
        hits.append(BASE + i2)
        i2 += 1
out.append(f"=== rank 写回 (and [..+0x2d],0xf8) {len(hits)} 处 ===")
for h in hits:
    out.append(f"  {h:#010x}  func={host(h):#010x}")
# 去重函数宿主
fns = sorted(set(host(h) for h in hits))
out.append(f"\n涉及函数 {len(fns)} 个: " + " ".join(hex(f) for f in fns))

# 每个函数附近找 or byte[..+0x2d], imm （设置新 rank）和 merit 比较
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False
for fn in fns:
    idx = funcs.index(fn)
    end = funcs[idx + 1] if idx + 1 < len(funcs) else fn + 0x200
    code = mem[fn - BASE: end - BASE]
    asm = list(md.disasm(code, fn))
    # 找 +0x2d 相关的 or/add 与附近的 cmp 阈值
    rel = []
    for ins in asm:
        if "0x2d" in ins.op_str and ("or" in ins.mnemonic or "add" in ins.mnemonic) and "0xf8" not in ins.op_str:
            rel.append(("OR/ADD", ins))
        if "0x2d" in ins.op_str and "and" in ins.mnemonic:
            rel.append(("AND", ins))
    out.append(f"\n--- func {fn:#010x} ({len(asm)} 条)  rank 相关写入 ---")
    for tag, ins in rel[:10]:
        out.append(f"  [{tag}] {ins.address:#010x}  {ins.mnemonic} {ins.op_str}")

open(os.path.join(HERE, "_rankwrite.txt"), "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out[:120]))
