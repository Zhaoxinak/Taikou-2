"""analyze_ents.py — 用 BSDATA 母表的 father_id 关系, 反推运行时实体的真正父亲字段偏移
输入: .rev/ents_dump.json (dump_ents.py 产物) + ../data/officers.json (BSDATA 导出)
"""
import json, os, struct
from collections import defaultdict, Counter

REV = os.path.dirname(os.path.abspath(__file__))
ents = json.load(open(os.path.join(REV, 'ents_dump.json'), encoding='utf-8'))
off = json.load(open(r'F:\Games\Taikou 2\data\officers.json', encoding='utf-8'))
print('runtime ents', len(ents), ' bsdata', len(off))

# ---------- 1. 姓名对齐 ----------
def norm(s):
    return (s or '').strip().replace(' ', '')

rt_by_name = defaultdict(list)
for e in ents:
    rt_by_name[norm(e['surname']) + norm(e['given'])].append(e)

bs_by_name = defaultdict(list)
for o in off:
    bs_by_name[norm(o['surname']) + norm(o['given'])].append(o)

pair = {}          # bsdata id -> runtime slot
dupname = 0
for o in off:
    k = norm(o['surname']) + norm(o['given'])
    c = rt_by_name.get(k, [])
    if len(c) == 1 and len(bs_by_name[k]) == 1:
        pair[o['id']] = c[0]['slot']
    elif len(c) > 1:
        dupname += 1
print('唯一姓名对齐成功: %d / %d (同名冲突 %d)' % (len(pair), len(off), dupname))

rt = {e['slot']: e for e in ents}
def raw(e):
    return bytes.fromhex(e['raw'])

# ---------- 2. 用 BSDATA 父子关系在 47B 里搜偏移 ----------
rels = [(o['id'], o['father_id']) for o in off if o['father_id'] != 0xFFFF]
print('BSDATA 父子关系 %d 条' % len(rels))
usable = [(c, f) for c, f in rels if c in pair and f in pair]
print('父子双方都在运行时在场: %d 条' % len(usable))

score = Counter()
per_off_hits = Counter()
for off_b in range(0, 45):
    hit = 0
    for c, f in usable:
        e = rt[pair[c]]
        v = struct.unpack_from('<H', raw(e), off_b)[0]
        if v == rt[pair[f]]['oid']:
            hit += 1
    if hit:
        score[hit] = off_b
for hit, off_b in sorted(score.items(), reverse=True)[:8]:
    print('  offset +0x%02X : 命中 %d / %d' % (off_b, hit, len(usable)))

# ---------- 3. 用 dword 也试一遍 ----------
sc4 = Counter()
for off_b in range(0, 43):
    hit = 0
    for c, f in usable:
        e = rt[pair[c]]
        v = struct.unpack_from('<I', raw(e), off_b)[0]
        if v == rt[pair[f]]['oid']:
            hit += 1
    if hit:
        sc4[hit] = off_b
for hit, off_b in sorted(sc4.items(), reverse=True)[:5]:
    print('  [dword] offset +0x%02X : 命中 %d / %d' % (off_b, hit, len(usable)))

# ---------- 4. 最可能的偏移: 打印所有与 BSDATA father 相符的样本 ----------
best_off = None
if score:
    best_hit = max(score)
    best_off = score[best_hit]
if best_off is None:
    print('!! 没有任何偏移能重现 BSDATA 父子关系 -> 运行时+0x1d 类字段另有语义')
else:
    print('\n=== 最优偏移 +0x%02X 的逐条验证 ===' % best_off)
    for c, f in usable:
        e = rt[pair[c]]
        v = struct.unpack_from('<H', raw(e), best_off)[0]
        ok = 'OK ' if v == rt[pair[f]]['oid'] else 'BAD'
        print('  %s %s %s(oid %d) 字段=%d  期望父=%d %s' %
              (ok, e['surname'], e['given'], e['oid'], v, rt[pair[f]]['oid'],
               rt[pair[f]]['surname'] + rt[pair[f]]['given']))

# ---------- 5. 柴田胜家全家 ----------
print('\n=== 柴田胜家 runtime 实体全 47B ===')
for e in ents:
    if e['surname'] == '柴田':
        print('  slot%3d oid%4d %s %s' % (e['slot'], e['oid'], e['surname'], e['given']))
        h = e['raw']
        for i in range(0, 47, 16):
            print('     +%02X: %s' % (i, ' '.join(h[i * 2 + j * 2:i * 2 + j * 2 + 2] for j in range(min(16, 47 - i)))))
print('\n=== BSDATA 中 oid 对应姓柴田/佐久间 ===')
for o in off:
    if o['surname'] in ('柴田', '佐久间'):
        print('  id%3d %s %s father=%s  lord=%s city=%s  对齐slot=%s' %
              (o['id'], o['surname'], o['given'], o['father_id'], o['lord'], o['city'], pair.get(o['id'])))
