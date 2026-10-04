"""解析 UPX 存根重建 IAT 所用的导入信息（位于 RVA 0x130000）"""
import struct

dump = open(r'F:\Games\Taikou 2\Taikou2 Original\.rev\clean_dump.bin', 'rb').read()

def rd(rva):
    return dump[rva:rva+4]

def cstr(rva):
    e = dump.index(b'\0', rva)
    return dump[rva:e].decode('latin1')

BLOB = 0x130000
NAME_BASE = 0x1319C4   # 存根里 lea eax,[eax+esi+0x1319C4], esi=0x401000
IAT_BASE_OFF = 0x1000  # add ebx,esi

edi = BLOB
dlls = []
while True:
    name_off, iat_off = struct.unpack_from('<II', dump, edi)
    if name_off == 0:
        print('[终止] name_off==0 于 RVA %s' % hex(edi))
        break
    dll_rva = name_off + NAME_BASE
    iat_rva = iat_off + IAT_BASE_OFF
    dll = cstr(dll_rva)
    edi += 8
    # 函数名序列：每项 0x01 + name + 0x00，遇 0x00 结束
    funcs = []
    while True:
        b = dump[edi]
        if b == 0:
            edi += 1
            break
        if b != 0x01:
            print('  !! 期望标记字节 0x01, 实际 %02x @%s' % (b, hex(edi)))
        fn = cstr(edi + 1)
        funcs.append(fn)
        edi += 1 + len(fn) + 1
    dlls.append((dll, dll_rva, iat_rva, funcs))
    print('%-14s name@%s IAT@%s  函数 %d 个' % (dll, hex(dll_rva), hex(iat_rva), len(funcs)))

print()
total = 0
for dll, dr, ir, fs in dlls:
    total += len(fs)
    # 检查 dump 里这些 IAT 槽是否已被填成真实地址
    vals = [struct.unpack_from('<I', dump, ir + 4*i)[0] for i in range(len(fs))]
    nz = sum(1 for v in vals if v)
    print('%-14s IAT@%s: %d 槽, 非零 %d, 首值 %s, 末值 %s' % (
        dll, hex(ir), len(vals), nz, hex(vals[0]) if vals else '-', hex(vals[-1]) if vals else '-'))
    print('     前几个:', ', '.join(fs[:6]))
print()
print('DLL 数:', len(dlls), ' 函数总数:', total)
