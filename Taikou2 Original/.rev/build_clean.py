"""
用干净的内存镜像重建一个可正常运行的未加壳 exe。

输入: .rev/clean_dump.bin  (UPX 存根执行完毕后的内存映像)
输出: TAIK2W95_clean.exe    (纯净脱壳版，不含任何外部补丁)
"""
import struct

DUMP = r'F:\Games\Taikou 2\Taikou2 Original\.rev\clean_dump.bin'
PACKED = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95.exe'
OUT = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_clean.exe'

dump = bytearray(open(DUMP, 'rb').read())
packed = open(PACKED, 'rb').read()

FILE_ALIGN = 0x200
SECT_ALIGN = 0x1000
IMAGEBASE = 0x400000
OEP = 0xF44B0

def cstr(rva):
    e = dump.index(b'\0', rva)
    return dump[rva:e].decode('latin1')

# ---------- 1. 解析导入表 ----------
BLOB = 0x130000
NAME_BASE = 0x1329C4   # name_off + 0x1000(esi) + 0x1319C4
IAT_BASE = 0x1000

edi = BLOB
imports = []
while True:
    name_off, iat_off = struct.unpack_from('<II', dump, edi)
    if name_off == 0:
        break
    dll = cstr(name_off + NAME_BASE)
    iat_rva = iat_off + IAT_BASE
    edi += 8
    funcs = []
    while True:
        b = dump[edi]
        if b == 0:
            edi += 1
            break
        assert b == 0x01, '意外的标记字节 %02x @%s' % (b, hex(edi))
        fn = cstr(edi + 1)
        funcs.append(fn)
        edi += 1 + len(fn) + 1
    imports.append({'dll': dll, 'iat': iat_rva, 'funcs': funcs})

assert len(imports) == 4, 'DLL 数不对: %d' % len(imports)
for m in imports:
    print('%-14s IAT@%s  %d 个函数' % (m['dll'], hex(m['iat']), len(m['funcs'])))
    assert m['dll'], 'DLL 名为空!'
print('函数总数:', sum(len(m['funcs']) for m in imports))

# ---------- 2. 规划 .idata 布局 ----------
IDATA_RVA = 0x133000
off = 0
desc_rva = IDATA_RVA + off
off += (len(imports) + 1) * 20
for m in imports:
    m['int_rva'] = IDATA_RVA + off
    off += (len(m['funcs']) + 1) * 4
off = (off + 3) & ~3
for m in imports:
    m['dllname_rva'] = IDATA_RVA + off
    off += len(m['dll']) + 1
off = (off + 1) & ~1
for m in imports:
    for fn in m['funcs']:
        m.setdefault('hn', []).append(IDATA_RVA + off)
        off += 2 + len(fn) + 1
        off = (off + 1) & ~1
idata_size = off
idata_raw = (idata_size + FILE_ALIGN - 1) // FILE_ALIGN * FILE_ALIGN

idata = bytearray(idata_raw)
def w8(rva, b):
    idata[rva - IDATA_RVA:rva - IDATA_RVA + len(b)] = b
def w32(rva, v):
    struct.pack_into('<I', idata, rva - IDATA_RVA, v)

# 描述符
p = desc_rva
for m in imports:
    w32(p, m['int_rva']); w32(p+4, 0); w32(p+8, 0)
    w32(p+12, m['dllname_rva']); w32(p+16, m['iat'])
    p += 20
w32(p, 0); w32(p+4, 0); w32(p+8, 0); w32(p+12, 0); w32(p+16, 0)

# DLL 名
for m in imports:
    w8(m['dllname_rva'], m['dll'].encode() + b'\0')

# hint/name 表 + INT + 覆盖镜像里的 IAT
for m in imports:
    for i, fn in enumerate(m['funcs']):
        hn = m['hn'][i]
        struct.pack_into('<H', idata, hn - IDATA_RVA, 0)          # hint = 0
        w8(hn + 2, fn.encode() + b'\0')
        w32(m['int_rva'] + 4*i, hn)        # INT
        struct.pack_into('<I', dump, m['iat'] + 4*i, hn)   # IAT(在 .text 里)
    w32(m['int_rva'] + 4*len(m['funcs']), 0)

# ---------- 3. 组装 PE ----------
text = bytes(dump[0x1000:0x1000+0xC3000])
data = bytes(dump[0xC4000:0xC4000+0x6E000])
rsrc = packed[0x6D800:0x6D800+0xC00] + b'\0' * (0x1000 - 0xC00)

secs = [
    (b'.text',  0x1000,   0xC3000, text,  0x60000020),
    (b'.data',  0xC4000,  0x6E000, data,  0xC0000040),
    (b'.rsrc',  0x132000, 0x1000,  rsrc,  0x40000040),
    (b'.idata', 0x133000, idata_size, bytes(idata), 0xC0000040),
]

# DOS 头（沿用原文件前 0xb0 字节，e_lfanew=0xb0）
dos = bytearray(packed[:0xB0])
hdr_size = 0x400
pe = bytearray(hdr_size)
pe[:0xB0] = dos

def p32(o, v): struct.pack_into('<I', pe, o, v)
def p16(o, v): struct.pack_into('<H', pe, o, v)

p32(0xB0, 0x00004550)                       # PE\0\0
p16(0xB4, 0x014C)                           # i386
p16(0xB6, len(secs))                        # NumberOfSections
p32(0xB8, 0x38FD73C8)                       # TimeDateStamp（沿用原值）
p32(0xBC, 0); p32(0xC0, 0)
p16(0xC4, 0xE0)                             # SizeOfOptionalHeader
p16(0xC6, 0x010F)                           # Characteristics

opt = 0xC8
p16(opt, 0x010B)                            # PE32
p16(opt+2, 5); p16(opt+3, 10)               # linker 5.10 (占位)
p32(opt+4, 0xC3000)                         # SizeOfCode
p32(opt+8, 0x6F000)                         # SizeOfInitializedData
p32(opt+12, 0)                              # SizeOfUninitializedData
p32(opt+16, OEP)                            # AddressOfEntryPoint
p32(opt+20, 0x1000)                         # BaseOfCode
p32(opt+24, 0xC4000)                        # BaseOfData
p32(opt+28, IMAGEBASE)                      # ImageBase
p32(opt+32, SECT_ALIGN); p32(opt+36, FILE_ALIGN)
p16(opt+40, 4); p16(opt+42, 0)              # OS ver
p16(opt+44, 0); p16(opt+46, 0)              # Image ver
p16(opt+48, 4); p16(opt+50, 0)              # Subsystem ver
p32(opt+52, 0)
SIZE_OF_IMAGE = 0x136000
p32(opt+56, SIZE_OF_IMAGE)
p32(opt+60, hdr_size)
p32(opt+64, 0)                              # CheckSum
p16(opt+68, 2)                              # Subsystem = GUI
p16(opt+70, 0)                              # DllCharacteristics
p32(opt+72, 0x100000); p32(opt+76, 0x1000)  # Stack reserve/commit
p32(opt+80, 0x100000); p32(opt+84, 0x1000)  # Heap reserve/commit
p32(opt+88, 0)
p32(opt+92, 16)                             # NumberOfRvaAndSizes

dd = opt + 96
for i in range(16):
    p32(dd + i*8, 0); p32(dd + i*8 + 4, 0)
p32(dd + 1*8, desc_rva); p32(dd + 1*8 + 4, (len(imports)+1)*20)   # IMPORT
p32(dd + 2*8, 0x132000); p32(dd + 2*8 + 4, 0x9C4)                 # RESOURCE

# 节表
so = opt + 0xE0
fo = hdr_size
for name, rva, vs, blob, chars in secs:
    rawsize = len(blob)
    rawsize_a = (rawsize + FILE_ALIGN - 1) // FILE_ALIGN * FILE_ALIGN
    pe[so:so+8] = name.ljust(8, b'\0')
    p32(so+8, vs); p32(so+12, rva)
    p32(so+16, rawsize); p32(so+20, fo)
    p32(so+24, 0); p32(so+28, 0); p16(so+32, 0); p16(so+34, 0)
    p32(so+36, chars)
    so += 40
    fo += rawsize_a

out = bytearray(pe)
for name, rva, vs, blob, chars in secs:
    rawsize_a = (len(blob) + FILE_ALIGN - 1) // FILE_ALIGN * FILE_ALIGN
    out += blob + b'\0' * (rawsize_a - len(blob))

open(OUT, 'wb').write(bytes(out))
print('\n已生成:', OUT, len(out), '字节')
print('  入口点 RVA =', hex(OEP), ' SizeOfImage =', hex(SIZE_OF_IMAGE))
print('  节:', [(n.decode(), hex(r), hex(v)) for n, r, v, _, _ in secs])
