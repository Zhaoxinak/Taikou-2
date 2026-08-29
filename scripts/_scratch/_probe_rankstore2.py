# -*- coding: utf-8 -*-
"""补搜 +0x2d 立即数写回：c6 ?? 2d (mov r/m8,imm8) 与 80 ?? 2d ?? (and/or r/m8,imm8)。"""
import struct, os, bisect
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
mem = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()

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

hits = []
o = 0
while o < len(mem) - 4:
    b0 = mem[o]
    if b0 in (0xc6, 0x80):
        b1 = mem[o + 1]
        if (b1 & 0xC0) == 0x40 and mem[o + 2] == 0x2d:
            imm = mem[o + 3]
            hits.append((BASE + o, b0, b1, imm))
            o += 4
            continue
    o += 1

out = [f"=== +0x2d 立即数写回 {len(hits)} 处 (c6=mov imm / 80=and,or imm) ==="]
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False
for va, b0, b1, imm in hits:
    fn = host(va)
    # 反汇编该处上下文
    asm = list(md.disasm(mem[va - BASE - 12: va - BASE + 24], va - 12))
    ctx = " | ".join(f"{ins.address:#010x}:{ins.mnemonic} {ins.op_str}" for ins in asm)
    out.append(f"  {va:#010x} (func {fn:#010x}) op=0x{b0:02x} imm={imm:#x}  {ctx}")

open(os.path.join(HERE, "_rankstore2.txt"), "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out[:120]))
