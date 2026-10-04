"""
逐 RVA 比对「干净内存镜像 clean_dump.bin」与「HD 版」，列出所有差异区间。
clean_dump.bin 偏移 == RVA；HD.exe：.text 偏移=RVA-0xC00，其余节偏移==RVA。
"""
import re

HD = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_HD.exe'
DUMP = r'F:\Games\Taikou 2\Taikou2 Original\.rev\clean_dump.bin'
CLEAN = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_clean.exe'

h = open(HD, 'rb').read()
d = open(DUMP, 'rb').read()
c = open(CLEAN, 'rb').read()

# HD: .text VA 0x1000 raw 0x400 ; .data VA 0xc4000 raw 0xc4000 ; .rsrc 0x132000 raw 0x132000 ; .idata 0x133000 raw 0x133000
def hd_off(rva):
    if rva < 0xC4000:
        return rva - 0xC00
    return rva

def cl_off(rva):
    return rva - 0xC00          # clean.exe: .text/.data 都是 RVA-0xC00

N = min(0x133000, len(d), len(c))

# 收集差异
diffs = []
i = 0
while i < N:
    if hd_off(i) is None or hd_off(i) >= len(h):
        i += 1
        continue
    if d[i] != h[hd_off(i)]:
        j = i
        while j < N and hd_off(j) < len(h) and d[j] != h[hd_off(j)]:
            j += 1
        diffs.append((i, j))
        i = j
    else:
        i += 1

# 合并相邻（间隔 < 8 字节）
merged = []
for a, b in diffs:
    if merged and a - merged[-1][1] < 8:
        merged[-1] = (merged[-1][0], b)
    else:
        merged.append((a, b))

print('=== HD 版 vs 干净镜像：差异区间 (RVA) ===')
print('共 %d 段\n' % len(merged))
for a, b in merged:
    seg_d = d[a:b]
    seg_h = h[hd_off(a):hd_off(a) + (b - a)]
    # 判断所在节
    if a < 0xC4000:
        sect = '.text'
    elif a < 0x132000:
        sect = '.data'
    else:
        sect = '.rsrc'
    kind = ''
    if all(x == 0x90 for x in seg_h):
        kind = '全部 NOP'
    elif seg_h[:1] == b'\xb8' and seg_h[5:6] == b'\xc3':
        kind = '返回立即数'
    elif seg_h[:1] == b'\xe9':
        import struct
        rel = struct.unpack('<i', seg_h[1:5])[0] if len(seg_h) >= 5 else 0
        tgt = (a + 5 + rel) & 0xFFFFFFFF
        kind = 'jmp -> RVA 0x%X' % tgt
    print('[%-5s] RVA 0x%06X..0x%06X  (%d 字节)  %s' % (sect, a, b, b - a, kind))
    print('    clean: %s' % seg_d[:40].hex(' '))
    print('    HD   : %s' % seg_h[:40].hex(' '))
    if sect != '.rsrc':
        print('    clean.exe 文件偏移 0x%06X' % cl_off(a))
    print()
