import os, struct
BASE = 0x400000
IMG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_unpacked_mem.bin')
data = open(IMG, 'rb').read()

import capstone
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = True

# Find `8a ?? 1b 00 00 00`  =>  mov r8, [reg+reg+0x1b]  (disp32 = 0x1b)
hits = []
i = 0
while i + 6 <= len(data):
    if data[i] == 0x8a and data[i+3] == 0x1b and data[i+4] == 0x00 and data[i+5] == 0x00:
        # modrm at i+1 must be mod=10 (disp32): high 2 bits = 0b10
        modrm = data[i+1]
        if (modrm & 0xc0) == 0x80:
            hits.append(BASE + i)
    i += 1
print('=== candidate `mov r8,[base+idx+0x1b]` sites : %d ===' % len(hits))

for va in hits:
    off = va - BASE
    code = data[max(0, off-0x30): off+0x20]
    found = False
    for ins in md.disasm(code, va - 0x30):
        if ins.address == va:
            found = True
        if found:
            print('  0x%06x: %-10s %s' % (ins.address, ins.mnemonic, ins.op_str))
        if found and ins.address > va + 0x14:
            break
    print('  ---')
    if len(hits) > 40:
        break
