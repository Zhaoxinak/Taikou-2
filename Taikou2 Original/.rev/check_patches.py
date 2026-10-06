import struct
print('Reading exe...')
d = open('../TAIK2W95_bigb.exe', 'rb').read()
print('Read %d bytes' % len(d))
pe = struct.unpack_from('<I', d, 0x3C)[0]
print('PE header at 0x%X' % pe)
nsec = struct.unpack_from('<H', d, pe + 6)[0]
opt_sz = struct.unpack_from('<H', d, pe + 0x14)[0]
print('Number of sections: %d, optional header size: %d' % (nsec, opt_sz))
text_raw = None
text_rva = None
sec_start = pe + 0x18 + opt_sz
for i in range(nsec):
    off = sec_start + i * 0x28
    name = d[off:off+8].rstrip(b'\x00').decode('ascii', errors='replace')
    rva = struct.unpack_from('<I', d, off + 12)[0]
    raw = struct.unpack_from('<I', d, off + 20)[0]
    print('Section %d: %s RVA=0x%X raw=0x%X' % (i, name, rva, raw))
    if name == '.text':
        text_raw = raw
        text_rva = rva

if text_raw:
    # Check 0x4CD47C (dispatch table slot 7) - VA, need to convert to RVA
    rva = 0x4CD47C - 0x400000
    fo = text_raw + (rva - text_rva)
    val = struct.unpack_from('<I', d, fo)[0]
    print('0x4CD47C (table slot 7): 0x%08X (expected 0x00550FD0)' % val)

    # Check 0x4CD390 (cmp limit)
    rva = 0x4CD390 - 0x400000
    fo = text_raw + (rva - text_rva)
    val = d[fo]
    print('0x4CD390 (cmp limit): 0x%02X (expected 0x07)' % val)

    # Check 0x4CD563 (hook)
    rva = 0x4CD563 - 0x400000
    fo = text_raw + (rva - text_rva)
    val = d[fo:fo+5]
    print('0x4CD563 (hook): %s (expected e9xxxxxxxx)' % val.hex())

    # Check what's at 0x550FD0 (foster handler)
    edata_raw = None
    edata_rva = None
    for i in range(nsec):
        off = sec_start + i * 0x28
        name = d[off:off+8].rstrip(b'\x00').decode('ascii', errors='replace')
        rva = struct.unpack_from('<I', d, off + 12)[0]
        raw = struct.unpack_from('<I', d, off + 20)[0]
        if name == '.edata':
            edata_raw = raw
            edata_rva = rva
            break
    if edata_raw:
        rva = 0x550FD0 - 0x400000
        fo = edata_raw + (rva - edata_rva)
        print('0x550FD0 (foster handler) first 16 bytes: %s' % d[fo:fo+16].hex())
