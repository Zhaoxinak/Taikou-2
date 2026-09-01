# -*- coding: utf-8 -*-
"""Search the unpacked EXE for soldier-type (兵种) name strings (GBK) to map
the 9 SECT_A rows (unit classes) to names. Also locate the known 3-broad-class
table referenced by unitTypeName (0x43e150 &0x50bfe8)."""
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

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
BASE = 0x400000

candidates = ['足轻','步兵','骑兵','铁炮','弓兵','枪兵','忍者','僧兵','水军','攻城',
              '长枪','骑马','洋枪','弩兵','骑马铁炮','弓','枪','歩兵','騎馬','鉄砲']
found = {}
for name in candidates:
    try:
        enc = name.encode('gbk')
    except Exception:
        continue
    i = 0
    hits = []
    while True:
        i = MEM.find(enc, i)
        if i < 0: break
        hits.append(i + BASE)
        i += 1
    if hits:
        found[name] = hits

print('=== candidate name hits (VA) ===')
for name, hits in found.items():
    print('  %s : %d hits -> %s' % (name, len(hits), [hex(h) for h in hits[:8]]))

# For each hit, dump 40 bytes around to see if it's a packed name table (9 names)
print('\n=== context dumps for found names ===')
seen = set()
for name, hits in found.items():
    for h in hits[:3]:
        if h in seen: continue
        seen.add(h)
        chunk = MEM[h - BASE - 24: h - BASE + 48]
        # try to decode a run of CJK as GBK null/space-separated
        txt = ''
        j = 0
        while j < len(chunk):
            b = chunk[j:j+2]
            try:
                c = b.decode('gbk')
                txt += c
                j += 2
            except Exception:
                txt += '.'
                j += 1
        print('  @%08x %s -> %s' % (h, name, txt))
