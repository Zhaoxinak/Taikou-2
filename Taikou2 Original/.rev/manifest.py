import re, struct, sys

path = 'TAIK2W95_HD.exe'
d = open(path, 'rb').read()
# .text VA 0x1000 raw 0x400 ; .data VA 0xc4000 raw 0xc4000
def off(rva):
    return rva - 0x1000 + 0x400 if rva < 0xc4000 else rva - 0xc4000 + 0xc4000

pat = re.compile(rb'([@A-Z]):([!-~]{1,60}?)\x00')
seen = {}
rows = []
for m in pat.finditer(d):
    raw = m.start()
    try:
        rva = raw - 0x400 + 0x1000 if raw < 0xc4000 else raw - 0xc4000 + 0xc4000
    except Exception:
        rva = raw
    name = m.group(0)[:-1].decode('latin1')
    if raw in seen: continue
    seen[raw] = 1
    rows.append((raw, rva, m.group(1).decode('latin1'), m.group(2).decode('latin1')))

# 只保留看起来像"资源清单"的：同一区域内成串出现、且与磁盘上真实文件同名
import os
real = set(x.upper() for x in os.listdir('.'))
rows.sort()
print("命中 %d 条 '<前缀>:<文件名>' 形式的串" % len(rows))
from collections import Counter
print("前缀分布:", Counter(r[2] for r in rows).most_common())

print("\n=== 与磁盘真实文件同名的条目 ===")
hit = [r for r in rows if r[3].upper() in real]
print("共 %d 条" % len(hit))
for raw, rva, p, n in hit:
    print("  file@%-8s rva@%s  %s:%s" % (hex(raw), hex(rva), p, n))

print("\n=== 全部条目（按文件偏移） ===")
for raw, rva, p, n in rows:
    mark = "*" if n.upper() in real else " "
    print(" %s %-8s %s:%s" % (mark, hex(raw), p, n))
