# -*- coding: utf-8 -*-
"""chk_recmap.py —— 找出 BSDATA 记录 -> 实体 的字节映射(真机 ents_dump 反推)
输出 -> _recmap.txt
"""
import json, os, struct

ROOT = r'F:\Games\Taikou 2\Taikou2 Original'
REV = os.path.join(ROOT, '.rev')
R, NREC = 59, 700
BSD = open(os.path.join(ROOT, 'BSDATA1.TR2.orig'), 'rb').read()
flags = open(os.path.join(ROOT, 'SNDATA1.TR2'), 'rb').read()[0x14:0x14 + NREC]
live = [i for i in range(NREC) if flags[i]]
ents = json.load(open(os.path.join(REV, 'ents_dump.json'), encoding='utf-8'))
out = open(os.path.join(REV, '_recmap.txt'), 'w', encoding='utf-8')
w = lambda *a: print(*a, file=out)

# 每个实体字节, 在所有在场记录里找同值出现过的记录偏移 -> 统计最优偏移
cand = {}
for k in range(min(60, len(live))):
    e = ents[k]
    rr = BSD[live[k] * R: live[k] * R + R]
    raw = bytes.fromhex(e['raw'])
    for i in range(47):
        vals = [j for j in range(R) if rr[j] == raw[i]]
        cand.setdefault(i, {})[tuple(vals)] = cand.setdefault(i, {}).get(tuple(vals), 0) + 1

w('实体偏移 -> 记录偏移 候选(60 槽投票, 列出票数最高几种):')
best = {}
for i in sorted(cand):
    top = sorted(cand[i].items(), key=lambda x: -x[1])[:3]
    w('  ent+0x%02x: %s' % (i, ['%s x%d' % (str(list(v)), c) for v, c in top]))

# 直接并排打印 3 个槽
for k in (0, 1, 5):
    e = ents[k]
    rr = BSD[live[k] * R: live[k] * R + R]
    w('\n槽 %d (在场序) oid %d' % (k, live[k]))
    w('  rec  %s' % rr.hex())
    w('  ent  %s' % bytes.fromhex(e['raw']).hex())
    w('  姓名表读得: given=%r surname=%r' % (e['given'], e['surname']))
out.close()
print('-> .rev/_recmap.txt')
