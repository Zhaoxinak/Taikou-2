# -*- coding: utf-8 -*-
"""穷举找 switch 跳表：连续 >=N 个 dword 全部落在 .text（不要求是 call 目标）。"""
import struct, sys, json
BASE = 0x400000
mem = open('_unpacked_mem.bin','rb').read()
N = len(mem)
TLO, THI = 0x401000, 0x4f4000
MINRUN = int(sys.argv[1]) if len(sys.argv) > 1 else 12
runs = []
i = 0
while i + 4 <= N:
    v = struct.unpack_from('<I', mem, i)[0]
    if TLO <= v < THI:
        j = i; items = []
        while j + 4 <= N:
            v2 = struct.unpack_from('<I', mem, j)[0]
            if TLO <= v2 < THI:
                items.append(v2); j += 4
            else: break
        if len(items) >= MINRUN:
            runs.append((BASE + i, items))
        i = j
    else:
        i += 4
runs.sort(key=lambda r: -len(r[1]))
kept = []
for va, items in runs:
    if any(kva <= va < kva + 4*len(ki) for kva, ki in kept): continue
    kept.append((va, items))
print(f'跳表候选 {len(kept)} 张 (run>={MINRUN})')
out = []
for va, items in kept:
    out.append({'va': hex(va), 'n': len(items), 'targets': [hex(x) for x in items]})
    print(f'{va:#08x} n={len(items):3d} [{hex(va)}..{hex(va+4*len(items))}]  ' + ' '.join(hex(x) for x in items[:10]))
json.dump(out, open('_jmptabs.json','w',encoding='utf-8'), indent=1)
