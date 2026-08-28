#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""提取 HJMAPDAT.DAT：38 场战斗 × 1700B 记录 = 180B(9×20 兵种/阵形/计略表) + 760B(40×19 地形) + 760B(40×19 部署)。
   兵种表按 nibble 解码（每字节 2 个 0-15 属性）。输出 hjmapdat_battles.json。"""
import struct, json, os

DATA = 'F:/Games/Taikou2'
hj = open(os.path.join(DATA, 'HJMAPDAT.DAT'), 'rb').read()
assert len(hj) == 64600, len(hj)
NREC = len(hj) // 1700
assert NREC == 38

def nibbles(b):
    out = []
    for x in b:
        out.append(x & 0xF)
        out.append((x >> 4) & 0xF)
    return out

battles = []
# 地形码 = 低4位(类型, 0-15 共16种) + 高4位(修饰位)
TERRAIN_TYPES = {
    0x0:'空',0x1:'平地',0x2:'荒地',0x3:'草地',0x4:'森林',0x5:'河流',
    0x6:'山地',0x7:'桥',0x8:'?8',0x9:'?9',0xa:'?A',0xb:'?B',
    0xc:'?C',0xd:'城',0xe:'阵',0xf:'?F',
}
def terrain_decode(v):
    return TERRAIN_TYPES.get(v & 0xF, '?'), (v >> 4) & 0xF
# 部署字符（工作记忆：J/K/I/9/8/2/3/H/+/… 布阵字符）
DEPLOY_NAMES = {
    ord('0'):'空地',ord(' '):'空',ord('J'):'左军将',ord('K'):'左军兵',ord('I'):'左军',
    ord('9'):'右军将',ord('8'):'右军兵',ord('2'):'右军',ord('3'):'中军将',
    ord('H'):'中军兵',ord('+'):'中军',ord('/'):'左军特',ord('1'):'左',ord('7'):'右',ord('5'):'右特',
}

for ridx in range(NREC):
    rec = hj[ridx*1700:(ridx+1)*1700]
    A = rec[0:180]; B = rec[180:940]; C = rec[940:1700]
    # 9 rows x 20 bytes, decode as 40 nibbles each
    unit_rows = []
    all_nib = []
    for r in range(9):
        row = A[r*20:(r+1)*20]
        nib = nibbles(row)
        all_nib.extend(nib)
        unit_rows.append({'raw': list(row), 'nibbles': nib})
    # terrain 40x19: 低4位=地形类型(0-15)，高4位=修饰位
    terrain = []
    terr_type_hist = {}
    for y in range(19):
        row = []
        for x in range(40):
            v = B[y*40+x]
            t, m = terrain_decode(v)
            terr_type_hist[t] = terr_type_hist.get(t,0)+1
            row.append({'code': v, 'type': t, 'mod': m})
        terrain.append(row)
    # deploy 40x19 ascii
    deploy = []
    for y in range(19):
        row = C[y*40:(y+1)*40].decode('ascii','replace')
        deploy.append(row)
    # 统计 section A nibble 分布（判定 flags vs stats）
    hist = {}
    for n in all_nib:
        hist[n] = hist.get(n,0)+1
    battles.append({
        'id': ridx,
        'unit_table': unit_rows,          # 9 条 × 20B（nibble 解码在 nibbles 字段）
        'unit_nibble_hist': hist,
        'terrain': terrain,               # 40x19: {code,type,mod}
        'terrain_type_hist': terr_type_hist,
        'deploy': deploy,
    })

# 整体分析：section A 在所有 38 场中是否含 >1 的非零 nibble（即真有数值）
global_hist = {}
for b in battles:
    for k,v in b['unit_nibble_hist'].items():
        global_hist[k] = global_hist.get(k,0)+v
print('=== section A 全局 nibble 分布 (0-15) 跨 38 场 ===')
for k in range(16):
    print('  nibble %2d: %6d 次' % (k, global_hist.get(k,0)))
nonzero = sum(v for k,v in global_hist.items() if k>1)
print('  值>1 的 nibble 总数:', nonzero)

# 地形类型分布（低4位=16种）
gter = {}
for b in battles:
    for k,v in b['terrain_type_hist'].items():
        gter[k]=gter.get(k,0)+v
print('=== 地形类型全局分布 (低4位, 16种) ===')
for k in sorted(gter):
    print('  %-4s: %6d' % (k, gter[k]))

# 打印第 0 场部署图样例
print('=== 第0场 部署图 (40x19) ===')
for row in battles[0]['deploy']:
    print('  ' + row)

with open('hjmapdat_battles.json','w',encoding='utf-8') as f:
    json.dump(battles, f, ensure_ascii=False)
print('\nsaved hjmapdat_battles.json (%d battles)' % len(battles))
