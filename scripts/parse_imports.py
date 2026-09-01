#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse TAIK2W95.exe import table -> dict IAT_VA -> function name.
Also reports the IAT slot VAs for file-I/O APIs we want to hook."""
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>

import struct, sys

EXE = _ROOT + '/Taikou2 Original/TAIK2W95.exe'
d = open(EXE, "rb").read()
assert d[:2] == b"MZ"
e_lfanew, = struct.unpack_from("<I", d, 0x3c)
pe_off = e_lfanew
assert d[pe_off:pe_off+2] == b"PE"
# COFF header at pe_off+4; optional header at pe_off+4+20
coff = pe_off + 4
machine, nsec = struct.unpack_from("<HH", d, coff)
optsize = struct.unpack_from("<H", d, coff + 16)[0]
nopt = optsize
oh = pe_off + 24  # optional header start (PE sig 4 + coff 20)
assert optsize >= 0x60
# sections: after optional header
sh_off = oh + optsize
secs = []
print("DEBUG nopt=%d optsize=%d oh=%d sh_off=%d nsec=%d filesize=%d" % (nopt, optsize, oh, sh_off, nsec, len(d)))
for i in range(nsec):
    b = sh_off + i * 40
    if b + 40 > len(d):
        print("  skip section %d: past EOF at %d" % (i, b))
        break
    name = d[b:b+8].split(b"\x00")[0].decode("latin1")
    vsize = struct.unpack_from("<I", d, b + 8)[0]
    vaddr = struct.unpack_from("<I", d, b + 12)[0]
    rawsize = struct.unpack_from("<I", d, b + 16)[0]
    rawptr = struct.unpack_from("<I", d, b + 20)[0]
    secs.append((name, vaddr, rawptr, rawsize, vsize))
    print("  sec %d %r vaddr=%08x rawptr=%08x rawsize=%d vsize=%d" % (i, name, vaddr, rawptr, rawsize, vsize))

def rv2o(rva):
    for _, vaddr, rawptr, rawsize, vsize in secs:
        if vaddr <= rva < vaddr + max(vsize, rawsize):
            return rawptr + (rva - vaddr)
    return None

imp_rva, imp_size = struct.unpack_from("<II", d, oh + 0x60 + 8 * 12)  # DataDirectory[1] = IMPORT
imp_o = rv2o(imp_rva)
assert imp_o is not None, "import dir not in sections"

# walk IMAGE_IMPORT_DESCRIPTOR (20 bytes), last is zero
p = imp_o
results = []  # (iat_va, name)
while True:
    od1, od2, _, _, fthk = struct.unpack_from("<IIIII", d, p)
    if od1 == 0 and od2 == 0 and fthk == 0:
        break
    dllname_o = rv2o(od2)
    dll = d[dllname_o:d.index(b"\x00", dllname_o)].decode("latin1")
    # INT at od1 (OriginalFirstThunk); IAT at fthk
    int_o = rv2o(od1)
    iat_o = rv2o(fthk)
    idx = 0
    while True:
        thunk = struct.unpack_from("<I", d, iat_o + idx * 4)[0]
        if thunk == 0:
            break
        if thunk & 0x80000000:
            fname = "ord%d" % (thunk & 0x7fffffff)
        else:
            nmo = rv2o(thunk) + 2
            ne = d.index(b"\x00", nmo)
            fname = d[nmo:ne].decode("latin1")
        results.append((fthk + idx * 4, fname, dll))
        idx += 1
    p += 20

for iat_va, fname, dll in results:
    if fname in ("OpenFile", "_lread", "_lwrite", "_lclose", "_llseek",
                 "GlobalAlloc", "GlobalLock", "GlobalUnlock", "GlobalFree",
                 "GetCurrentDirectoryA", "GetDriveTypeA", "CreateFileA",
                 "ReadFile", "HeapAlloc", "HeapFree"):
        print("IAT %08x  %s  (%s)" % (iat_va, fname, dll))
print("--- total imports:", len(results))
