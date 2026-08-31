# -*- coding: utf-8 -*-
# 字节扫描 0x5179b8 所有引用，dump 上下文找大名阈值比较
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin", "rb").read()
BASE = 0x400000
N = len(MEM)
cs = Cs(CS_ARCH_X86, CS_MODE_32)
cs.detail = True

PAT = bytes([0xb8, 0x79, 0x51, 0x00])  # 0x5179b8 LE
hits = []
i = 0
while i + 4 <= N:
    if MEM[i:i+4] == PAT:
        hits.append(BASE + i)
    i += 1
print(f"0x5179b8 references (as disp32): {len(hits)}")
for h in hits:
    # dump 60 bytes before + 40 after (context around the reference)
    start = max(BASE, h - 80)
    off = start - BASE
    print(f"\n---- context @ ref {h:#010x} ----")
    md = cs.disasm(MEM[off:off+200], start)
    cnt = 0
    for ins in md:
        mark = " <<<" if ins.address == h else ""
        print(f"  {ins.address:#010x}  {ins.mnemonic} {ins.op_str}{mark}")
        cnt += 1
        if cnt > 30:
            break
