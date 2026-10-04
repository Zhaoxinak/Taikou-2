# -*- coding: utf-8 -*-
"""静态核对: 从 big.exe 里取 .fdata, 反汇编 draw_detail, 并检查详情记录是否越界。"""
import struct, sys, os
sys.stdout.reconfigure(encoding='utf-8')

GAME = r'F:\Games\Taikou 2\Taikou2 Original'

def sec_of(path, want=b'.fdata'):
    b = open(path, 'rb').read()
    pe = struct.unpack_from('<I', b, 0x3C)[0]
    nsec = struct.unpack_from('<H', b, pe + 6)[0]
    opt = struct.unpack_from('<H', b, pe + 0x14)[0]
    tab = pe + 0x18 + opt
    base = struct.unpack_from('<I', b, pe + 0x34)[0]
    for i in range(nsec):
        o = tab + i * 40
        name = b[o:o + 8].rstrip(b'\0')
        va = struct.unpack_from('<I', b, o + 12)[0]
        sz = struct.unpack_from('<I', b, o + 8)[0]
        ptr = struct.unpack_from('<I', b, o + 20)[0]
        rsz = struct.unpack_from('<I', b, o + 16)[0]
        if name == want:
            return b, base + va, ptr, rsz
    return None, None, None, None

for exe in ['TAIK2W95_family.exe', 'TAIK2W95_big.exe']:
    p = os.path.join(GAME, exe)
    b, sva, sptr, ssz = sec_of(p)
    print('== %s  .fdata VA=0x%X ptr=0x%X size=0x%X (end 0x%X)' %
          (exe, sva, sptr, ssz, sva + ssz))

b, sva, sptr, ssz = sec_of(os.path.join(GAME, 'TAIK2W95_big.exe'))
SEC_VA = sva
POOL_VA = SEC_VA + 0x0E00
DTLTAB_VA = SEC_VA + 0x3100
RSTATE_VA = SEC_VA + 0x03C0
SELDET = RSTATE_VA + 0xF8
print('POOL_VA=0x%X  DTLTAB_VA=0x%X  SELDET_VA=0x%X' % (POOL_VA, DTLTAB_VA, SELDET))

def foff(va):
    return sptr + (va - SEC_VA)

# 详情表 u16 偏移, 逐条还原 [len1][line1][len2][line2], 检查是否越过 POOL 末
pool_end_va = SEC_VA + 0x3100   # POOL 区实际到详情表之前 (O_POOL..O_DETAILTAB)
import json
M = json.load(open(os.path.join(GAME, '.rev', 'tree_blobs.json')))
nnode = M['nnode']
bad = []
maxend = 0
for gi in range(nnode):
    off = struct.unpack_from('<H', b, foff(DTLTAB_VA + gi * 2))[0]
    ro = POOL_VA + off
    if ro >= SEC_VA + ssz:
        bad.append((gi, off, '越节')); continue
    l1 = b[foff(ro)]
    s1 = b[foff(ro) + 1:foff(ro) + 1 + l1].decode('gbk', 'replace')
    ro2 = ro + 1 + l1
    l2 = b[foff(ro2)] if ro2 < SEC_VA + ssz else None
    s2 = b[foff(ro2) + 1:foff(ro2) + 1 + (l2 or 0)].decode('gbk', 'replace') if l2 else ''
    end = ro + 1 + l1 + 1 + (l2 or 0)
    maxend = max(maxend, end)
    flag = ''
    if end > pool_end_va:
        flag = ' *OVERRUN(>%X)' % pool_end_va
        bad.append((gi, off, 'len%+%d' % (end - pool_end_va)))
    if l1 == 0:
        flag += ' *EMPTY'
    if gi < 6 or flag:
        print('  gi=%3d off=0x%04X l1=%d "%s" | l2=%d "%s"%s' %
              (gi, off, l1, s1, l2 or 0, s2, flag))
print('记录最远到达 VA=0x%X (POOL区末=0x%X, 节末=0x%X)' %
      (maxend, pool_end_va, SEC_VA + ssz))
print('越界/异常条数:', len(bad), bad[:20])
