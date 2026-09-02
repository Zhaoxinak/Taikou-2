import os, struct, sys
BASE = 0x400000
IMG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_unpacked_mem.bin')
data = open(IMG, 'rb').read()
N = len(data)

import capstone
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = True

def va_of(off):
    return BASE + off

def off_of(va):
    return va - BASE

# ---- 1. xref to skill-name table base 0x507b58 (LE bytes 58 7b 50 00) ----
needle = struct.pack('<I', 0x507b58)
xrefs = []
i = 0
while True:
    j = data.find(needle, i)
    if j < 0:
        break
    xrefs.append(va_of(j))
    i = j + 1
print('=== xrefs to 0x507b58 (skill name table) : %d ===' % len(xrefs))
for x in xrefs:
    print('  0x%06x' % x)

# ---- 2. disassemble each xref site, show ~60 ins around it ----
def disasm_around(va, before=0x40, after=0x60):
    off = off_of(va)
    lo = max(0, off - before)
    code = data[lo: off + after]
    print('\n--- around 0x%06x (load at 0x%06x) ---' % (va, va - before))
    for ins in md.disasm(code, va - before):
        mark = ' >>>' if ins.address == va else '    '
        print('  0x%06x:%s %-10s %s' % (ins.address, mark, ins.mnemonic, ins.op_str))

for x in xrefs[:8]:
    disasm_around(x)
