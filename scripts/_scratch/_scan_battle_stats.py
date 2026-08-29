#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scan EXE data section + decompressed battle files for unit/formation/strategy
stat tables: contiguous runs of numeric bytes with a clean periodic stride."""
import struct, sys
sys.path.insert(0, '.')
from real_assets import ls11_decompress

IMG = open('_unpacked_mem.bin', 'rb').read()
BASE = 0x400000

def autocorrel_run(buf, shift):
    n = len(buf) - shift
    if n <= 0: return 0.0
    c = 0
    for i in range(n):
        if buf[i] == buf[i+shift]: c += 1
    return c / n

STRIDES = [6,8,10,12,14,16,18,20,22,24,28,30,32,36,40,44,48,56,64,72,96,120,128]

def scan_buffer(buf, label, va_base=0):
    """Find runs of stat-like bytes, test periodicity."""
    found = []
    i = 0
    n = len(buf)
    # find maximal runs where bytes in [1,250] (exclude 0 and 0xff mostly)
    while i < n:
        if 1 <= buf[i] <= 250:
            j = i
            while j < n and 1 <= buf[j] <= 250:
                j += 1
            runlen = j - i
            if runlen >= 300:
                run = buf[i:j]
                best = (0.0, 0)
                for s in STRIDES:
                    if s >= runlen: break
                    v = autocorrel_run(run, s)
                    if v > best[0]:
                        best = (v, s)
                if best[0] >= 0.45:
                    found.append((label, va_base+i if va_base else i, runlen, best[1], best[0], run))
            i = j
        else:
            i += 1
    return found

print('=== SCAN EXE data section 0x401000..0x600000 ===')
exe_region = IMG[0x101000:0x200000]  # file offset; va_base = 0x400000+0x101000
hits = scan_buffer(exe_region, 'EXE', va_base=0x400000+0x101000)
for label, va, rl, s, m, run in hits:
    print(f'  {label} va=0x{va:06x} runlen={rl} stride={s} match={m*100:.0f}%')
    for k in range(min(3, rl//s)):
        rec = run[k*s:(k+1)*s]
        print('    rec%d:' % k, list(rec))

print('\n=== SCAN decompressed battle files ===')
FILES = {
    'TERRAIN.LZW': 'F:/Games/Taikou2/TERRAIN.LZW',
    'HKMAPNEW.LZW': 'F:/Games/Taikou2/HKMAPNEW.LZW',
    'HBMAP.LZW': 'F:/Games/Taikou2/HBMAP.LZW',
    'HJMAP.LZW': 'F:/Games/Taikou2/HJMAP.LZW',
    'HKMAP.LZW': 'F:/Games/Taikou2/HKMAP.LZW',
    'HJMAPDAT.DAT': 'F:/Games/Taikou2/HJMAPDAT.DAT',
    'GAIJI.TR2': 'F:/Games/Taikou2/GAIJI.TR2',
    'GRPDATA2.LZW': 'F:/Games/Taikou2/GRPDATA2.LZW',
    'MESSAGE2.LZW': 'F:/Games/Taikou2/MESSAGE2.LZW',
    'MESSAGE3.LZW': 'F:/Games/Taikou2/MESSAGE3.LZW',
    'MESSAGE4.LZW': 'F:/Games/Taikou2/MESSAGE4.LZW',
}
for name, path in FILES.items():
    raw = open(path, 'rb').read()
    if raw[:4] == b'LS11':
        try:
            out = ls11_decompress(raw)
        except Exception as e:
            print(f'  {name}: decompress error {e}'); continue
    else:
        out = raw
    print(f'--- {name}: {len(raw)}B -> {len(out)}B decompressed ---')
    hits = scan_buffer(out, name)
    if not hits:
        print('    (no periodic stat-like run >=300B)')
    for label, off, rl, s, m, run in hits:
        print(f'    {label} off={off} runlen={rl} stride={s} match={m*100:.0f}%')
        for k in range(min(3, rl//s)):
            rec = run[k*s:(k+1)*s]
            print('      rec%d:' % k, list(rec))
print('done')
