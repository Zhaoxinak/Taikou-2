# -*- coding: utf-8 -*-
"""Find loader functions: xref filename strings -> disassemble enclosing fn."""
import sys, struct, bisect
sys.path.insert(0, 'scripts')
import _fdis as F  # already wraps stdout

BASE = F.BASE
TEXT_START, TEXT_END = F.TEXT_START, F.TEXT_END
MEM = F.MEM

# filename string VAs (from recon scan) and table base
TARGETS = {
    'SAVEDATA@0x509592': 0x509592,
    'SNDATA1@0x5095a2': 0x5095a2,
    'SNDATA2@0x5095b2': 0x5095b2,
    'BSDATA1@0x5095c2': 0x5095c2,
    'BSDATA2@0x5095d2': 0x5095d2,
    'TOWNPOS@0x50c152': 0x50c152,
    'TOWNTBL@0x50c162': 0x50c162,
    'nametab@0x509590': 0x509590,
}

# opcodes that load an imm32 into something / reference it
def find_xrefs(va):
    pat = struct.pack('<I', va)
    out = []
    i = MEM.find(pat, TEXT_START - BASE, TEXT_END - BASE)
    while i >= 0:
        # preceding byte(s)
        b0 = MEM[i-1] if i-1 >= 0 else 0
        b1 = MEM[i-2] if i-2 >= 0 else 0
        kind = None
        if b0 == 0x68:           # push imm32
            kind = 'push'
        elif b0 in (0xb8,0xb9,0xba,0xbb,0xbc,0xbd,0xbe,0xbf):  # mov r32, imm32
            kind = 'mov r32'
        elif b1 == 0x8d and b0 in (0x05,0x0d,0x15,0x1d,0x25,0x2d,0x35,0x3d):  # lea r32,[imm32]
            kind = 'lea'
        elif b1 == 0xc7 and b0 == 0x05:  # mov [imm32], imm32
            kind = 'mov [imm]'
        elif b1 == 0xff and b0 == 0x35:  # push dword ptr [imm32]
            kind = 'push [imm]'
        if kind:
            site = BASE + i
            out.append((site, kind))
        i = MEM.find(pat, i+1, TEXT_END - BASE)
    return out

st = F.starts()
def enclosing(va):
    k = bisect.bisect_right(st, va)
    return st[k-1] if k-1 >= 0 else va

def main():
    seen_funcs = set()
    for name, va in TARGETS.items():
        xs = find_xrefs(va)
        if not xs:
            print(f"[no xref] {name}")
            continue
        print(f"\n##### {name}: {len(xs)} xref(s)")
        funcs = {}
        for site, kind in xs:
            fn = enclosing(site)
            funcs.setdefault(fn, []).append((site, kind))
        for fn, sites in sorted(funcs.items()):
            print(f"  fn {fn:#x}  xrefs={[(hex(s),k) for s,k in sites]}")
            seen_funcs.add(fn)
    # disassemble each unique loader fn (cap 1200 bytes)
    for fn in sorted(seen_funcs):
        F.dis_func(fn, 1400)

if __name__ == '__main__':
    main()
