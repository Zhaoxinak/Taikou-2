import struct

d = open(r'F:\Games\Taikou 2\Taikou2 Original\.rev\clean_dump.bin', 'rb').read()
h = open(r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_HD.exe', 'rb').read()

# clean: .text RVA 0x1000, .data RVA 0xc4000
# HD   : .text VA 0x1000 raw 0x400 ; .data VA 0xc4000 raw 0xc4000
def c_text(rva): return d[rva]
def h_text(rva): return h[rva - 0x1000 + 0x400]
def c_data(rva): return d[rva]
def h_data(rva): return h[rva]          # HD .data raw == VA

# 入口点确认
print('入口点 RVA 0xF44B0 (在 .data 内)')
print('  clean:', d[0xF44B0:0xF44B0+12].hex(' '))
print('  HD   :', h[0xF44B0:0xF44B0+12].hex(' '))
print('  一致:', d[0xF44B0:0xF44B0+64] == h[0xF44B0:0xF44B0+64])
print()

regions = [
    ('.text', 0x1000, 0x6d950, 0x6d95f),
    ('.text', 0x1000, 0x6d9ac, 0x6d9b1),
    ('.text', 0x1000, 0x6da60, 0x6da6b),
    ('.text', 0x1000, 0x6dc00, 0x6dc07),
    ('.text', 0x1000, 0x6e5ac, 0x6e5b1),
    ('.text', 0x1000, 0x97f30, 0x97f3b),
    ('.data', 0xc4000, 0x279bd, 0x279dd),
    ('.data', 0xc4000, 0x27a80, 0x27a8b),
    ('.data', 0xc4000, 0x2bb8f, 0x2bb9b),
    ('.data', 0xc4000, 0x2df55, 0x2df61),
    ('.data', 0xc4000, 0x2dfff, 0x2e04d),
    ('.data', 0xc4000, 0x6d343, 0x6d34f),
]

for sec, base, a, b in regions:
    lo = max(0, a - 16)
    hi = b + 16
    print('=== %s +%s .. +%s   (RVA %s..%s) ===' % (sec, hex(a), hex(b), hex(base+a), hex(base+b)))
    for tag, get in (('clean', c_text if sec == '.text' else c_data),
                     ('HD   ', h_text if sec == '.text' else h_data)):
        row = bytes(get(base + i) for i in range(lo, hi))
        mark = ''.join('^' if a <= base+i-base <= b else ' ' for i in range(lo, hi))
        print('  %s %s' % (tag, row.hex(' ')))
        print('       %s' % mark)
    print()
