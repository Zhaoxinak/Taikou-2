# -*- coding: utf-8 -*-
"""cavemap.py — 扫描补丁洞区(4KB)的全零空闲区间, 供新增数据/代码选址"""
import struct, sys, os

sys.stdout.reconfigure(encoding='utf-8')

EXE = os.path.join(r'F:\Games\Taikou 2\Taikou2 Original', sys.argv[1] if len(sys.argv) > 1 else 'TAIK2W95_family.exe')
CAVE_RVA, SZ, BASE_VA = 0x135000, 0x1000, 0x535000


def load_exe(path):
    d = open(path, 'rb').read()
    pe = struct.unpack_from('<I', d, 0x3c)[0]
    assert d[pe:pe + 4] == b'PE\0\0', 'not PE'
    nsec = struct.unpack_from('<H', d, pe + 6)[0]
    opt = struct.unpack_from('<H', d, pe + 20)[0]
    sections_start = pe + 24 + opt   # COFF 头 24B + 可选头
    secs = []
    for i in range(nsec):
        o = sections_start + i * 40
        nm = d[o:o + 8].rstrip(b'\x00').decode('latin1')
        vs, va, rs, ptr = struct.unpack_from('<IIII', d, o + 8)
        secs.append((nm, va, vs, rs, ptr))
    return d, secs


def r2o(secs, rva):
    for nm, va, vs, rs, ptr in secs:
        if va <= rva < va + max(vs, rs):
            return ptr + (rva - va)
    raise ValueError('RVA 0x%X 不在任何节' % rva)


def main():
    d, secs = load_exe(EXE)
    print('文件: %s' % os.path.basename(EXE))
    print('%-8s %-10s %-10s %-10s %s' % ('节', 'VAddr', 'VSize', 'RawSize', 'RawPtr'))
    for s in secs:
        print('%-8s 0x%08X 0x%08X 0x%08X 0x%X' % s)
    fo = r2o(secs, CAVE_RVA)
    blob = d[fo:fo + SZ]
    print()
    print('洞区 RVA 0x%06X -> file 0x%X, 大小 %d, 非零字节 %d'
          % (CAVE_RVA, fo, SZ, sum(1 for c in blob if c)))

    BLK = int(sys.argv[2]) if len(sys.argv) > 2 else 16
    runs, i = [], 0
    while i < SZ:
        z = blob[i] == 0
        j = i
        while j < SZ and (blob[j] == 0) == z:
            j += 1
        if z and j - i >= BLK:
            runs.append((BASE_VA + i, j - i))
        i = j
    print()
    print('=== 洞内全零可用区间 (>= %d B) ===' % BLK)
    tot = 0
    for va, n in runs:
        tot += n
        print('  0x%06X .. 0x%06X   %4d B' % (va, va + n - 1, n))
    print('  ------------------------------')
    print('  合计 %d B' % tot)


if __name__ == '__main__':
    main()
