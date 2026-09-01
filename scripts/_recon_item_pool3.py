#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recon 3: correct-stride name tables + build 27->8 cat mapping from 189 defs."""
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

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
IMG = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
BASE = 0x400000
def gb(va, n): return IMG[va - BASE: va - BASE + n]
def names_at(va, stride, count):
    out = []
    for i in range(count):
        b = gb(va + i * stride, stride)
        z = b.find(b'\x00')
        out.append(b[:z].decode('gbk', 'replace') if z >= 0 else b.decode('gbk', 'replace'))
    return out

print("=== 0x507ee0 stride5 (getShortName, cat 0..7) ===")
for i, s in enumerate(names_at(0x507ee0, 5, 8)):
    print(f"  cat{i} = {s!r}")

print("\n=== 0x507a50 stride13 (getSecondaryName, secondary-pool slot 0..19) ===")
for i, s in enumerate(names_at(0x507a50, 13, 20)):
    if s:
        print(f"  sec[{i}] = {s!r}")

print("\n=== 0x507ea8 stride7 (getTypeName, cat 0..7) ===")
for i, s in enumerate(names_at(0x507ea8, 7, 8)):
    print(f"  cat{i} = {s!r}")

# ---- 27 -> 8 mapping from the 189 def table (data-driven) ----
import json, os
def find_dir():
    for p in ('Taikou2 Original', os.path.join('..', 'Taikou2 Original')):
        if os.path.isdir(p): return p
    return None
d = find_dir()
raw = open(os.path.join(d, 'SNDATA1.TR2'), 'rb').read()
key = raw[0x12] ^ raw[0x13]
dec = bytes(b ^ key for b in raw[0x598:0x9f81])
def u16(b, i): return b[i] | (b[i+1] << 8)
CAT = {0:'茶碗·天目',1:'赤乐茶碗',2:'黄濑户茶碗',3:'茶入·茶罐',4:'花入·茶壶',5:'茶釜',
6:'名刀(村雨)',7:'刀',8:'胁差·短刀',9:'枪',10:'剃刀',11:'物语·书籍',12:'兵书·史书',
13:'绘词',14:'金',15:'银',16:'宝石',17:'宝石工艺品',18:'挂轴·画',19:'绘·画',20:'屏风',
21:'(空缺)',22:'时钟',23:'地球仪·天球仪',24:'望远镜',25:'南蛮物',26:'织物·香'}
POOLCAT = ['酒','书籍','道具','财宝','武器','南蛮物','美术品','茶具']
# empirical hypothesis mapping def-cat -> pool-cat
HYP = {0:7,1:7,2:7,3:7,4:7,5:7, 6:4,7:4,8:4,9:4,10:4, 11:1,12:1,13:1,
14:3,15:3,16:3,17:3, 18:6,19:6,20:6, 22:5,23:5,24:5,25:5, 26:2}
print("\n=== 189 def items: def-cat -> pool-cat distribution ===")
from collections import defaultdict
cnt = defaultdict(lambda: defaultdict(int))
for i in range(189):
    r = dec[32019 + i*19: 32019 + i*19 + 19]
    c = r[13]
    nm = r[:r.find(b'\x00')].decode('gbk', 'replace')
    pc = HYP.get(c, '?')
    cnt[c][pc] += 1
    # flag: if a def maps to multiple pool cats, flag it
for c in sorted(cnt):
    dist = dict(cnt[c])
    tag = '' if len(dist) == 1 else '  <-- MULTI'
    pcs = ','.join(f'{k}:{v}' for k, v in sorted(dist.items(), key=lambda x: str(x[0])))
    print(f"  def{c:2d} {CAT[c]:10s} -> {pcs}{tag}")
