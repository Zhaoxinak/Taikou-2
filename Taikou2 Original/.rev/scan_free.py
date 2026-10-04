"""scan_free.py — 扫描补丁 exe 里所有可用的空闲空间(连续零区)

用途: 树形家族树需要 ~2KB 数据(节点表 + 连线表 + 串池), 而现有代码洞(0x535000
      起 0x1000B)已用掉大半。本脚本解析 PE 节表, 逐节找 >= 最小尺寸的连续零区,
      并区分「可写节」(.data/.bss) 与「只读节」(.text/.rdata) —— 数据放只读节也行,
      只要运行时不被写。
"""
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8')
EXE = sys.argv[1] if len(sys.argv) > 1 else r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_family.exe'
MIN = int(sys.argv[2]) if len(sys.argv) > 2 else 512

d = open(EXE, 'rb').read()
print('file size 0x%X (%d)' % (len(d), len(d)))
pe = struct.unpack_from('<I', d, 0x3c)[0]
nsec = struct.unpack_from('<H', d, pe + 6)[0]
opt = struct.unpack_from('<H', d, pe + 20)[0]
ib = struct.unpack_from('<I', d, pe + 24 + 28)[0]      # ImageBase
secs = []
for i in range(nsec):
    o = pe + 24 + opt + i * 40
    nm = d[o:o + 8].rstrip(b'\x00').decode()
    vs, va, rs, ptr = struct.unpack_from('<IIII', d, o + 8)
    ch = struct.unpack_from('<I', d, o + 36)[0]
    secs.append(dict(nm=nm, va=va, vs=vs, rs=rs, ptr=ptr, ch=ch))
print('%-9s %-10s %-10s %-10s %-9s %s' % ('节', 'VAddr', 'VSize', 'RawSize', 'Chars', '文件区间'))
for s in secs:
    print('%-9s 0x%08X 0x%08X 0x%08X 0x%08X  0x%X..0x%X'
          % (s['nm'], s['va'], s['vs'], s['rs'], s['ch'], s['ptr'], s['ptr'] + s['rs']))

W = 0x80000000
print()
print('=== 各节内 >= %dB 的连续零区 ===' % MIN)
for s in secs:
    blob = d[s['ptr']:s['ptr'] + s['rs']]
    if not blob:
        continue
    writ = bool(s['ch'] & W)
    runs = []
    i = 0
    while i < len(blob):
        if blob[i] == 0:
            j = i
            while j < len(blob) and blob[j] == 0:
                j += 1
            if j - i >= MIN:
                runs.append((i, j - i))
            i = j
        else:
            i += 1
    if not runs:
        continue
    print('--- %s (%s) ---' % (s['nm'], '可写' if writ else '只读'))
    for off, ln in runs:
        a = s['va'] + off
        print('    VA 0x%06X..0x%06X  %5dB   file 0x%X' % (a, a + ln - 1, ln, s['ptr'] + off))

# 节表后是否有空位可加新节
sechdr_end = pe + 24 + opt + nsec * 40
sec_align = struct.unpack_from('<I', d, pe + 24 + 32)[0]
print()
print('节表结束于 0x%X, 节对齐 0x%X, 首个节 raw 0x%X -> 节表后空隙 %d 字节 (可容纳 %d 个新节头)'
      % (sechdr_end, sec_align, min(s['ptr'] for s in secs),
         min(s['ptr'] for s in secs) - sechdr_end, (min(s['ptr'] for s in secs) - sechdr_end) // 40))
