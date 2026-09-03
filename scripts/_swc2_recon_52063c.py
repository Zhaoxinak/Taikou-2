# 续242 recon: all instructions referencing 0x52063c in the unpacked image
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(os.path.join(_ROOT, 'scripts', '_unpacked_mem.bin'), 'rb').read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.skipdata = True

TARGET = 0x52063c
hits = []
# linear scan disassembly (same approach as prior refs)
for ins in md.disasm(MEM, BASE):
    if ins.op_str and (hex(TARGET)[2:] in ins.op_str.replace(' ', '')):
        # confirm actual immediate bytes present to avoid false positives
        b = ins.bytes.hex()
        if '3c065200' in b:  # little-endian 0x52063c
            hits.append((ins.address, ins.mnemonic, ins.op_str, b))

print(f"total refs to 0x52063c: {len(hits)}")
for a, m, o, b in hits:
    print(f"0x{a:06x}  {b:<24s} {m:<8s} {o}")
