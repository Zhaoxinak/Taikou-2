# -*- coding: utf-8 -*-
"""gen_oid_map.py —— 把族谱 124 人解析到 BSDATA(officers.json) 的真实 oid。

分级(置信度从高到低):
  exact         姓+名精确命中
  alias         手设别名(名字形态差异的史实人物)命中
  unique_given  名在 700 库里唯一命中
  fuzzy         名互为子串/共享字符的最近候选(标 ambiguous, 需人工复核)
  none          游戏真无档案 -> 详情走纯 tree_data 自绘 / 未来须合成 BSDATA 记录

产物 _tree_oid_map.json: 每 tree 人 -> {oid, conf, officer 关键档案, amb=[候选]}.
"""
import json, os, unicodedata
import tree_data as td

OFF = json.load(open(r'F:\Games\Taikou 2\data\officers.json', encoding='utf-8'))

# 别名: 族谱用名(姓,名) -> BSDATA 里的 (姓,名) 或直接 bushou_id
# 只填有把握的史实同人; 越保守越好, 拿不准的留 fuzzy/none 让人工判。
ALIAS = {
    ('丰臣', '秀吉'): ('木下', '藤吉郎'),   # 羽柴/木下/丰臣=同一人 id16
    ('丰臣', '秀长'): None,                 # 待定
    ('宁宁', ''): None,
}
# 更稳的别名用 bushou_id 直连(先据 given 精确查)
ALIAS_BY_GIVEN = {
    # 族谱名 -> officers 里的 given(唯一史实对应)
    '秀吉': '藤吉郎', '阿市': None, '茶茶': None, '宁宁': None, '浓姬': None,
}

by_exact = {}
by_given = {}
by_surn = {}
for r in OFF:
    sg = (r.get('surname', '').strip(), r.get('given', '').strip())
    by_exact.setdefault(sg, r)
    g = sg[1]
    if g:
        by_given.setdefault(g, []).append(r)
    if sg[0]:
        by_surn.setdefault(sg[0], []).append(r)


def norm(s):
    return unicodedata.normalize('NFKC', (s or '')).strip()


def cjk_dist(a, b):
    """粗略: 共享字符数多者优先, 长度差小者优先"""
    sa, sb = set(norm(a)), set(norm(b))
    inter = len(sa & sb)
    return -inter * 100 + abs(len(a) - len(b))


def collect_persons():
    seen, order = {}, []
    for fam in td.TREES:
        title_sur = fam[0]
        subj = fam[2]
        nodes = fam[3]
        for nd in nodes:
            sur, giv, rel, status = nd[1], nd[2], nd[3], nd[4]
            key = (norm(sur), norm(giv))
            if not key[1]:
                continue
            if key not in seen:
                seen[key] = {'sur': key[0], 'giv': key[1], 'rel': rel,
                             'status': status, 'fams': set()}
                order.append(key)
            seen[key]['fams'].add(norm(title_sur))
    return order, seen


def resolve(sur, giv):
    # exact
    r = by_exact.get((sur, giv))
    if r:
        return r['bushou_id'], 'exact', r, []
    # alias by given (唯一)
    ag = ALIAS_BY_GIVEN.get(giv)
    if ag:
        cands = by_given.get(ag, [])
        if len(cands) == 1:
            return cands[0]['bushou_id'], 'alias', cands[0], []
    # unique_given
    cands = by_given.get(giv, [])
    if len(cands) == 1:
        return cands[0]['bushou_id'], 'unique_given', cands[0], []
    if len(cands) > 1:
        return cands[0]['bushou_id'], 'ambiguous_given', cands[0], \
            [(c['surname'] + c['given'], c['bushou_id']) for c in cands]
    # fuzzy: 名互含 或 姓+名共享≥2字符
    pool = [c for c in by_given.get('*', [])] or OFF
    fuzzy = []
    for r in OFF:
        rg = norm(r['given']); rs = norm(r['surname'])
        if giv and (giv in rg or rg in giv):
            fuzzy.append(r); continue
        if sur and rs and (sur in rs or rs in sur) and (set(giv) & set(rg)):
            fuzzy.append(r)
    fuzzy.sort(key=lambda r: cjk_dist(r['given'], giv))
    if fuzzy:
        return fuzzy[0]['bushou_id'], 'fuzzy', fuzzy[0], \
            [(r['surname'] + r['given'], r['bushou_id']) for r in fuzzy[:4]]
    return None, 'none', None, []


def brief(r):
    if not r:
        return {}
    f = r.get('forces', {})
    return {
        'name': r.get('surname', '') + r.get('given', ''),
        'birth_year': r.get('birth_year'),
        'father_id': r.get('father_id'),
        'rank_name': r.get('rank_name'),
        'archetype_name': r.get('archetype_name'),
        'province': r.get('province'), 'city': r.get('city'),
        'lead': f.get('lead'), 'martial': f.get('martial'),
        'domestic': f.get('domestic'), 'diplomacy': f.get('diplomacy'),
        'charm': f.get('charm'),
    }


def main():
    order, seen = collect_persons()
    out, tally = [], {}
    for key in order:
        sur, giv = key
        oid, conf, rec, amb = resolve(sur, giv)
        tally[conf] = tally.get(conf, 0) + 1
        out.append({
            'sur': sur, 'giv': giv,
            'rel': seen[key]['rel'], 'status': seen[key]['status'],
            'fams': sorted(seen[key]['fams']),
            'oid': oid, 'conf': conf,
            'officer': brief(rec), 'amb': amb,
        })
    json.dump(out, open('_tree_oid_map.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('树内唯一人物=', len(out))
    print('置信度分布:', tally)
    print('\n== 非 exact/none 需复核的 (fuzzy/ambiguous) ==')
    for o in out:
        if o['conf'] in ('fuzzy', 'ambiguous_given', 'alias', 'unique_given'):
            print(' %-6s %s%s -> oid %s [%s] %s amb=%s' % (
                o['conf'], o['sur'], o['giv'], o['oid'],
                o['officer'].get('name', '?'), o['rel'],
                o['amb'][:3]))
    print('\n== none (游戏真无档案, 详情须自绘/合成) ==')
    nones = [o for o in out if o['conf'] == 'none']
    print('数量', len(nones))
    for o in nones[:80]:
        print('  ', o['sur'] + o['giv'], '|', o['rel'], '| fam', o['fams'])


if __name__ == '__main__':
    main()
