# -*- coding: utf8 -*-
"""probe_keyspace.py —— 培养系统地基探针 (只读, 不开游戏)

要钉死的三件事:
  A) 实体身份键空间: ent+0x00 / ent+0x02 到底是 槽号 还是 BSDATA oid
     (族谱 MOD 一直比 ent+0, 而父id 是 BSDATA oid -> 两者可能不在同一空间!)
  B) 父链反查的正确写法: 给定孩子实体, 用哪个键能找到父亲实体
  C) 五维/技能/生年在实体里的偏移复核 (+0x0a..0x0e / +0x0f..0x11 / +0x1b)

输入: .rev/ents_dump.json (运行期 dump) + F:/Games/Taikou 2/data/officers.json (BSDATA 700)
产物: .rev/_keyspace.txt
"""
import json, os, struct, sys
from collections import defaultdict, Counter

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

REV = os.path.dirname(os.path.abspath(__file__))
OUT = []


def w(s):
    OUT.append(s)
    print(s)


ents = json.load(open(os.path.join(REV, 'ents_dump.json'), encoding='utf-8'))
off = json.load(open(r'F:\Games\Taikou 2\data\officers.json', encoding='utf-8'))
w('运行期实体 %d 条 / BSDATA %d 条' % (len(ents), len(off)))

rt = {}
for e in ents:
    e['b'] = bytes.fromhex(e['raw'])
    rt[e['slot']] = e


def u16(b, o):
    return struct.unpack_from('<H', b, o)[0]


def u8(b, o):
    return b[o]


# ---------- 姓名 -> oid (BSDATA 母表) ----------
def norm(s):
    return (s or '').strip().replace(' ', '').replace('　', '')


bs_by_name = defaultdict(list)
for o in off:
    bs_by_name[norm(o['surname']) + norm(o['given'])].append(o['id'])
uniq = {k: v[0] for k, v in bs_by_name.items() if len(v) == 1}
w('BSDATA 唯一姓名 %d 组 (同名多人的已剔除)' % len(uniq))

# ---------- A) 键空间: 每槽 ent+0 / ent+2 与 姓名反查 oid 三方对照 ----------
tab = []
for e in ents:
    nm = norm(e['surname']) + norm(e['given'])
    oid_guess = uniq.get(nm)
    if oid_guess is None:
        continue
    tab.append((e['slot'], u16(e['b'], 0x00), u16(e['b'], 0x02), oid_guess, nm))

cnt = Counter()
for slot, a0, a2, oid, nm in tab:
    cnt['槽=ent0'] += slot == a0
    cnt['oid=ent0'] += oid == a0
    cnt['槽=ent2'] += slot == a2
    cnt['oid=ent2'] += oid == a2
    cnt['oid=槽'] += oid == slot
    cnt['样本'] += 1
w('\n--- A) 键空间三方对照 (%d 个姓名可唯一反查的槽) ---' % cnt['样本'])
for k in ('槽=ent0', 'oid=ent0', '槽=ent2', 'oid=ent2', 'oid=槽'):
    w('  %-9s %4d' % (k, cnt[k]))
w('  前 12 行样本 (slot, ent+0, ent+2, 姓名反查oid, 名):')
for r in tab[:12]:
    w('    %s' % (r,))

# ent+0 的取值范围/单调性: 是否就是"槽号自增"
mono = sum(1 for slot, a0, a2, oid, nm in tab if a0 == slot)
w('  ent+0 == 槽号 的比例: %d/%d' % (mono, len(tab)))
# 若是 oid 空间, ent+0 应等于 BSDATA id
w('  ent+0 == BSDATA oid 的比例: %d/%d' % (sum(1 for s, a0, a2, o, n in tab if a0 == o), len(tab)))

# ---------- B) 父链: 孩子 +0x1d 里存的到底是哪个空间 ----------
rels = [(o['id'], o['father_id']) for o in off if o.get('father_id', 0xFFFF) != 0xFFFF]
w('\n--- B) 父链 (BSDATA 父子 %d 条) ---' % len(rels))

# 孩子 oid -> 运行期槽 (用姓名)
oid2slot = {}
for slot, a0, a2, oid, nm in tab:
    oid2slot[oid] = slot
father_ok = Counter()
samples = []
for c_id, f_id in rels:
    cs = oid2slot.get(c_id)
    fs = oid2slot.get(f_id)
    if cs is None:
        continue
    b = rt[cs]['b']
    for fo in (0x1d, 0x02, 0x1f, 0x04, 0x06):
        got = u16(b, fo)
        if fs is not None:
            if got == f_id:
                father_ok['%02x=BSDATA父oid' % fo] += 1
            if got == fs:
                father_ok['%02x=父亲槽号' % fo] += 1
        if got == u16(b, 0):
            father_ok['%02x=自身ent0' % fo] += 1
    if fs is not None and len(samples) < 12:
        samples.append('子 %s(%s) oid%d 槽%d | 父 oid%d 槽%d | 实体+0x1d=%04X +0x02=%04X'
                       % (rt[cs]['surname'], rt[cs]['given'], c_id, cs, f_id, fs,
                          u16(b, 0x1d), u16(b, 0x02)))
w('  父子双方都在场的关系: %d 条' % sum(1 for c, f in rels if c in oid2slot and f in oid2slot))
for k, v in sorted(father_ok.items()):
    w('    %s : %d' % (k, v))
for s in samples:
    w('  ' + s)

# ---------- C) 五维/技能/生年 偏移复核 ----------
w('\n--- C) 字段偏移复核 ---')
# BSDATA 记录: 五维 0x16..0x1a, 技能 0x1b..0x1d, 生年 0x27, 父 0x29, 主君 0x36, 状态 0x38
# 若 ent[k]=rec[k+12] 则 五维在 ent+0x0a..0x0e, 技能 ent+0x0f..0x11, 生年 ent+0x1b, 父 ent+0x1d
offbyid = {o['id']: o for o in off}
hit = Counter()
tot = 0
for slot, a0, a2, oid, nm in tab:
    o = offbyid.get(oid)
    b = rt[slot]['b']
    tot += 1
    f = o.get('forces') or {}
    vals = [f.get(k) for k in ('lead', 'martial', 'domestic', 'diplomacy', 'charm')]
    for k in range(5):
        if vals[k] is not None and vals[k] == u8(b, 0x0a + k):
            hit['五维+%02x' % (0x0a + k)] += 1
    sl = o.get('skill_levels')
    if sl:
        ok = 0
        for i, lvl in enumerate(sl):
            if (u8(b, 0x0f + (i >> 2)) >> ((i & 3) * 2)) & 3 == lvl:
                ok += 1
        hit['技能位组>=8/10'] += ok >= 8
        hit['技能位组==10'] += ok == 10
    by = o.get('birth_year')
    if by is not None:
        v = u8(b, 0x1b) & 0x7f
        # 引擎口径 1500+byte 与 1490+byte 都试
        if 1490 + v == by or 1500 + v == by:
            hit['生年+1b'] += 1
    fid = o.get('father_id')
    if fid is not None and u16(b, 0x1d) == fid:
        hit['父+1d'] += 1
    ld = o.get('lord')
    if ld is not None and u16(b, 0x2a) == ld:
        hit['主君+2a'] += 1
    st = o.get('status_word')
    if st is not None and u16(b, 0x2c) == st:
        hit['状态+2c'] += 1
    for nm2, key, ent_o in (('体力上限+20', 'stamina_max', 0x20), ('体力现役+21', 'stamina', 0x21),
                            ('忠诚+29', 'loyalty', 0x29), ('俸禄+28', 'salary', 0x28),
                            ('野心+23', 'ambition', 0x23), ('国+24', 'province', 0x24)):
        v = o.get(key)
        if v is not None and len(b) > ent_o and u8(b, ent_o) == v:
            hit[nm2] += 1
w('  样本 %d 槽; 逐字段命中:' % tot)
for k in sorted(hit):
    w('    %-10s %d' % (k, hit[k]))

# officers.json 键名打印一条, 防止字段名猜错
w('  officers.json 键: %s' % sorted(off[0].keys()))
w('  第一条: %s' % {k: off[0][k] for k in sorted(off[0])})

open(os.path.join(REV, '_keyspace.txt'), 'w', encoding='utf-8').write('\n'.join(OUT) + '\n')
