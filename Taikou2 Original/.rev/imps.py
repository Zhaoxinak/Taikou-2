import struct, sys, os

def rva2off(secs, rva):
    for (name, vs, va, rs, ra) in secs:
        if va <= rva < va + max(vs, rs):
            return ra + (rva - va)
    return None

def load(path):
    data = open(path, 'rb').read()
    e_lfanew = struct.unpack_from('<I', data, 0x3C)[0]
    coff = e_lfanew + 4
    machine, nsec, *_ = struct.unpack_from('<HHIIIHH', data, coff)
    opt_off = coff + 20
    magic = struct.unpack_from('<H', data, opt_off)[0]
    p = opt_off + 28
    (imagebase, sectAlign, fileAlign) = struct.unpack_from('<III', data, p)
    p += 68
    nRva = struct.unpack_from('<I', data, opt_off + 92)[0]
    dd_off = opt_off + 96
    dirs = [struct.unpack_from('<II', data, dd_off + i*8) for i in range(16)]
    sec_off = opt_off + 224
    secs = []
    for i in range(nsec):
        o = sec_off + i*40
        name = data[o:o+8].rstrip(b'\0').decode('latin1')
        vs, va, rs, ra = struct.unpack_from('<IIII', data, o+8)
        secs.append((name, vs, va, rs, ra))
    return data, secs, dirs, imagebase, opt_off

def show_imports(path):
    data, secs, dirs, imagebase, _ = load(path)
    print("=" * 70)
    print("IMPORTS:", path)
    irva, isz = dirs[1]
    if not irva:
        print("  none")
        return
    off = rva2off(secs, irva)
    print("  import dir RVA %s -> file off %s" % (hex(irva), hex(off)))
    n = 0
    while True:
        d = data[off:off+20]
        if len(d) < 20: break
        origft, tds, fwd, nameRva, ftRva = struct.unpack('<IIIII', d)
        if nameRva == 0: break
        noff = rva2off(secs, nameRva)
        nm = data[noff:data.index(b'\0', noff)].decode('latin1')
        # thunks
        funcs = []
        toff = rva2off(secs, origft if origft else ftRva)
        if toff:
            while True:
                t = struct.unpack_from('<I', data, toff)[0]
                if t == 0: break
                if t & 0x80000000:
                    funcs.append("ord:%d" % (t & 0xFFFF))
                else:
                    ho = rva2off(secs, t)
                    if ho is None: break
                    hint = struct.unpack_from('<H', data, ho)[0]
                    fn = data[ho+2:data.index(b'\0', ho+2)].decode('latin1')
                    funcs.append(fn)
                toff += 4
        print("  %-16s (%d)" % (nm, len(funcs)))
        print("     ", ", ".join(funcs) if funcs else "<none>")
        off += 20
        n += 1
        if n > 60: break

for p in sys.argv[1:]:
    show_imports(p)
