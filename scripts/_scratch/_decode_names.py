# -*- coding: utf-8 -*-

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
import sys, io, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()

def gbk(b):
    # split at first NUL, decode GBK
    n = b.find(b'\x00')
    if n >= 0:
        b = b[:n]
    return b.decode('gbk', 'replace') if b else '(empty)'

def dump_table(va, stride, n, label):
    print(f'\n=== {label} @ {va:#x}  stride={stride} n={n} ===')
    for i in range(n):
        off = va - BASE + i * stride
        raw = MEM[off: off + stride]
        print(f'  [{i:2d}] {raw.hex()}  {gbk(raw)}')

dump_table(0x5099d8, 5, 20, 'CORPS_ATTRS_A (stride5)')
dump_table(0x509a78, 5, 20, 'CORPS_ATTRS_B (stride5)')
dump_table(0x50953c, 8, 12, 'CASTLE_FIELD_NAMES (stride8)')

# search 0x509000-0x50b000 for a ~20-entry name table: long runs of GBK pairs (2-byte lead 0x81-0xfe)
print('\n=== scan for candidate 20-attr name tables (stride 4..12, >=12 GBK entries) ===')
from collections import defaultdict
# find all GBK-leading bytes and treat as string starts
import re
regions = []
i = 0x509000 - BASE
end = 0x50b000 - BASE
# naive: scan for sequences of >=3 GBK chars (each 2 bytes high>=0x81)
strs = []
j = i
while j < end:
    ch = MEM[j]
    if 0x81 <= ch <= 0xfe and j + 1 < end:
        try:
            s = MEM[j:j+2].decode('gbk')
            # count consecutive CJK
            k = j
            chars = []
            while k + 1 < end and 0x81 <= MEM[k] <= 0xfe:
                c = MEM[k:k+2]
                try:
                    chars.append(c.decode('gbk'))
                    k += 2
                except Exception:
                    break
            if len(chars) >= 2:
                strs.append((j + BASE, ''.join(chars)))
            j = k
        except Exception:
            j += 1
    else:
        j += 1
# group by stride: for each VA, check if next 12 VAs at stride S are all string starts
cands = defaultdict(list)
for S in range(4, 13):
    for idx in range(len(strs)):
        va0, t0 = strs[idx]
        ok = True
        seq = [t0]
        for m in range(1, 20):
            tv = va0 + m * S
            found = None
            # binary-ish search
            for va, t in strs:
                if va == tv:
                    found = t
                    break
            if found is None:
                # allow partial (stop)
                ok = False
                break
            seq.append(found)
        if len(seq) >= 12:
            cands[S].append((va0, seq))
for S in sorted(cands):
    for va0, seq in cands[S][:6]:
        print(f'  stride={S} @{va0:#x}: {seq[:20]}')
