# -*- coding: utf-8 -*-
"""穷举法找「字符串指针表」：连续 >=5 个 dword 都精确指向某条串首 → 判定为指针表。
不假设表长/表址/段落，全映像 4 字节步进扫描。"""
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

import struct, json, sys
BASE = 0x400000
mem = open(_ROOT + '/scripts/_unpacked_mem.bin','rb').read()
N = len(mem)

# 1) 串首集合
strstart = {}
for line in open('_all_strings.txt', encoding='utf-8'):
    va, ln, txt = line.rstrip('\n').split('\t', 2)
    strstart[int(va,16)] = txt

minrun = int(sys.argv[1]) if len(sys.argv)>1 else 5

runs = []
i = 0
step = 4
while i + 4 <= N:
    v = struct.unpack_from('<I', mem, i)[0]
    if v in strstart:
        j = i
        items = []
        while j + 4 <= N:
            v2 = struct.unpack_from('<I', mem, j)[0]
            if v2 in strstart and BASE + j not in strstart:
                items.append(v2)
                j += 4
                if j - i > 4000: break
            else:
                break
        if len(items) >= minrun:
            runs.append((BASE + i, items))
        i = j
    else:
        i += step

# 去重（包含关系保留最长）
runs.sort(key=lambda r: (-len(r[1]), r[0]))
kept = []
covered_ends = set()
for va, items in runs:
    key = (va, len(items))
    dup = False
    for kva, kitems in kept:
        if kva <= va and va + 4*len(items) <= kva + 4*len(kiitems) if False else False:
            dup = True
    # 简单去重：若起点被已有更长表覆盖则跳过
    if any(kva <= va < kva + 4*len(kiitems) for kva, kiitems in kept):
        continue
    kept.append((va, items))

print(f'指针表候选 {len(kept)} 张（run>={minrun}）\n')
out = []
for va, items in kept:
    strs = [strstart.get(v, '?') for v in items]
    out.append({'va': hex(va), 'n': len(items), 'ptrs': [hex(v) for v in items], 'strs': strs})
    print(f'{va:#08x}  n={len(items):3d}  ' + ' | '.join(strs[:16]))
    if len(strs) > 16:
        print('      ...+', ' | '.join(strs[16:40]))
json.dump(out, open('_ptr_tables.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
