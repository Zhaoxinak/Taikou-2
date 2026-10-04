import struct, sys, os

def parse_pe(path):
    data = open(path, 'rb').read()
    print("=" * 60)
    print(path, "size =", len(data), hex(len(data)))
    if data[:2] != b'MZ':
        print("  not MZ")
        return
    e_lfanew = struct.unpack_from('<I', data, 0x3C)[0]
    print("  e_lfanew =", hex(e_lfanew))
    if data[e_lfanew:e_lfanew+4] != b'PE\0\0':
        print("  no PE sig at", hex(e_lfanew))
        return
    coff = e_lfanew + 4
    machine, nsec, tds, psym, nsym, sizeopt, chars = struct.unpack_from('<HHIIIHH', data, coff)
    print("  machine =", hex(machine), "numSections =", nsec)
    print("  TimeDateStamp =", hex(tds), " Characteristics =", hex(chars))
    opt_off = coff + 20
    magic = struct.unpack_from('<H', data, opt_off)[0]
    print("  opt magic =", hex(magic), "(0x10b=PE32, 0x20b=PE32+)")
    if magic == 0x10b:
        pass
        p = opt_off
        # Optional header standard fields (PE32): magic, majorLinker, minorLinker,
        # sizeOfCode, sizeOfInitializedData, sizeOfUninitializedData,
        # addressOfEntryPoint, baseOfCode, baseOfData
        (magic, linkerM, linkerm, szCode, szInit, szUninit,
         ep, baseCode, baseData) = struct.unpack_from('<HBBIIIIII', data, p)
        p += 28
        (imagebase, sectAlign, fileAlign, osM, osm, imgM, imgm,
         subM, subm, reserved, szImg, szHdr, checksum,
         subsys, dllchars, szStackRes, szStackCom, szHeapRes, szHeapCom,
         ldrflags, nRva) = struct.unpack_from('<IIIHHHHHHIIIIHHIIIIII', data, p)
        data_dirs_off = p + 68
        print("  linker %d.%d  entrypoint RVA = %s  imagebase = %s" % (linkerM, linkerm, hex(ep), hex(imagebase)))
        print("  SizeOfImage =", hex(szImg), " SizeOfHeaders =", hex(szHdr), " checksum =", hex(checksum), " subsystem =", subsys)
        print("  sectionAlign =", hex(sectAlign), " fileAlign =", hex(fileAlign))
        names = ["EXPORT","IMPORT","RESOURCE","EXCEPTION","SECURITY","RELOC","DEBUG","ARCH",
                 "GLOBALPTR","TLS","LOADCFG","BOUND","IAT","DELAY","CLRHDR","RESERVED"]
        print("  --- data directories ---")
        for i in range(nRva):
            rva, sz = struct.unpack_from('<II', data, data_dirs_off + i*8)
            if rva or sz:
                print("    %-10s RVA=%-10s size=%s" % (names[i] if i < 16 else str(i), hex(rva), hex(sz)))
        sec_off = opt_off + 224
    else:
        print("  unsupported magic")
        return
    print("  --- sections ---")
    for i in range(nsec):
        o = sec_off + i*40
        name = data[o:o+8].rstrip(b'\0').decode('latin1')
        vs, va, rs, ra, pr, pn, nl, lnc = struct.unpack_from('<IIIIIIHH', data, o+8)
        # raw size / raw addr are the 3rd and 5th fields
        (vs, va_, rs, ra, pr, pn, nl, ch) = struct.unpack_from('<IIIIIIHH', data, o+8)
        print("    %-10s VS=%-9s VA=%-9s RawSize=%-9s Raw=%-9s chars=%s" % (
            name, hex(vs), hex(va), hex(rs), hex(ra), hex(ch)))
    # entropy + packer signature scan
    print("  --- heuristics ---")
    import math
    def ent(b):
        if not b: return 0.0
        from collections import Counter
        c = Counter(b)
        n = len(b)
        return -sum((v/n)*math.log2(v/n) for v in c.values())
    print("    whole-file entropy = %.3f" % ent(data))
    sigs = {
        b'UPX0': 'UPX', b'UPX1': 'UPX', b'UPX2': 'UPX', b'UPX!': 'UPX',
        b'ASPack': 'ASPack', b'aPLib': 'aPLib', b'PECompact': 'PECompact',
        b'PEC2': 'PECompact2', b'FSG!': 'FSG', b'Petite': 'Petite',
        b'!EPack': 'EPack', b'WWPACK': 'WWPACK', b'PKLITE': 'PKLITE',
        b'LZEXE': 'LZEXE', b'MEW': 'MEW', b'NSPack': 'NSPack',
        b'NsPacK': 'NSPack', b'Themida': 'Themida', b'WinLicense': 'WinLicense',
        b'VMProtect': 'VMProtect', b'Armadillo': 'Armadillo', b'.aspack': 'ASPack',
        b'.nsp': 'NSPack', b'LCC': 'LCC', b'MASKPE': 'MASKPE',
    }
    found = set()
    for s, n in sigs.items():
        idx = data.find(s)
        if idx != -1:
            found.add((n, hex(idx)))
    if found:
        for n, i in sorted(found):
            print("    SIG %s at %s" % (n, i))
    else:
        print("    no known packer signature (first 4MB scan)")
    return data

for p in sys.argv[1:]:
    parse_pe(p)
