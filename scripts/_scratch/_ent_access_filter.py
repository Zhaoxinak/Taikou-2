# -*- coding: utf-8 -*-
"""Find real entity+0x1c / +0x1f accesses (filter stack false positives)."""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
import struct, re

BASE = 0x400000
mem = open("scripts/_unpacked_mem.bin", "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)

# Find ×47 entity addressing: lea r,[r+r*2]; shl r,4; sub r,r; add r,0x519868
# Then within next 0x60 bytes, look for [reg + 0x1c/1f/20]

ENT = 0x519868
hits = {0x1c: [], 0x1d: [], 0x1e: [], 0x1f: [], 0x20: []}

# Scan for add reg, 0x519868 after ×47 pattern-ish, then look ahead
needle = struct.pack("<I", ENT)
start = 0
while True:
    i = mem.find(needle, start)
    if i < 0 or i >= 0xF0000:
        break
    va = BASE + i
    # disasm from va-0x20 to va+0x80
    code = mem[i - 0x30:i + 0xA0]
    base_va = va - 0x30
    # check if this looks like entity addressing (sub/lea nearby before)
    pre = " | ".join(f"{ins.mnemonic} {ins.op_str}" for ins in md.disasm(mem[i-0x20:i+5], va-0x20))
    is_ent = ("shl" in pre and "sub" in pre) or ("lea" in pre and "0x519868" in pre)
    if not is_ent:
        # also accept: add esi, 0x519868 after lea/shl/sub in longer window
        pre2 = " ".join(f"{ins.mnemonic}" for ins in md.disasm(mem[i-0x30:i+5], va-0x30))
        if not ("shl" in pre2 and "sub" in pre2):
            start = i + 1
            continue
    # look ahead for mem ops with +0x1c..0x20 on a register (not esp)
    for ins in md.disasm(mem[i:i + 0x80], va):
        if "esp" in ins.op_str:
            continue
        for d in (0x1c, 0x1d, 0x1e, 0x1f, 0x20):
            if re.search(rf"\[(?:\w+) \+ {d:#x}\]", ins.op_str) or re.search(rf"\[(?:\w+)\+{d:#x}\]", ins.op_str):
                hits[d].append((ins.address, ins.mnemonic, ins.op_str, va))
    start = i + 1

for d in (0x1c, 0x1d, 0x1e, 0x1f, 0x20):
    print(f"\n===== entity+{d:#x} after ×47 ({len(hits[d])}) =====")
    seen = set()
    for a, m, o, src in hits[d]:
        if a in seen:
            continue
        seen.add(a)
        print(f"  {a:#x}: {m:8} {o}   (via {src:#x})")

# Also scan for test/cmp/and on [reg+0x1c] with imm in code, then verify ×47 in function
print("\n===== +0x1c bit tests (ecx/esi/edi/ebx) =====")
# F6 41/46/47/43 1c XX = test byte [reg+0x1c], imm
# 80 79/7e/7f/7b 1c XX = cmp
# 80 61/66/67/63 1c XX = and
patterns = []
for modrm_reg, regname in [(0x41, "ecx"), (0x46, "esi"), (0x47, "edi"), (0x43, "ebx"),
                           (0x01, "eax"), (0x02, "edx")]:
    # test byte [reg+disp], imm8 = F6 /0
    for opcode, name in [(b"\xF6", "test"), (b"\x80", "alu")]:
        pass

# brute: find  , 0x1c  in disasm of known-good by searching bytes: 1c followed by checking
for off in range(0x1000, 0xF0000 - 8):
    # modrm with disp8=0x1c, mod=01
    modrm = mem[off]
    if ((modrm >> 6) & 3) != 1:
        continue
    if mem[off + 1] != 0x1c:
        continue
    rm = modrm & 7
    if rm not in (1, 3, 6, 7, 0, 2):  # ecx ebx esi edi eax edx
        continue
    # try disasm at off-1 and off-2
    for back in (1, 2, 0):
        ins = next(md.disasm(mem[off - back:off - back + 12], BASE + off - back), None)
        if not ins:
            continue
        if ins.address <= BASE + off < ins.address + ins.size and "+ 0x1c" in ins.op_str and "esp" not in ins.op_str and "ebp" not in ins.op_str:
            if ins.mnemonic in ("test", "cmp", "and", "or", "mov", "movzx", "movsx"):
                print(f"  {ins.address:#x}: {ins.mnemonic:8} {ins.op_str}")
            break
