import struct
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()
BASE = 0x400000
def rd(va, n):
    return MEM[va - BASE: va - BASE + n]

vals = list(struct.unpack_from('<32i', MEM, 0x5176a8 - BASE))
nz = [(i, v) for i, v in enumerate(vals) if v != 0]
print('伏兵 0x5176a8 (32xint32): nonzero =', nz if nz else 'ALL ZERO')

print('\n填埋 格式串（内联，直接读字节）:')
for nm, va in [('0x50360c', 0x50360c), ('0x503620', 0x503620), ('0x503630', 0x503630),
              ('0x503634', 0x503634), ('0x503644', 0x503644), ('0x5029b8', 0x5029b8), ('0x5035fc', 0x5035fc)]:
    raw = rd(va, 24)
    s = ''
    for b in raw:
        if b == 0:
            break
        if 32 <= b < 127:
            s += chr(b)
        else:
            s += '\\x%02x' % b
    print('  %s: "%s"' % (nm, s))

print('\n修复 0x503560 全表:', list(struct.unpack_from('<16H', MEM, 0x503560 - BASE)))
