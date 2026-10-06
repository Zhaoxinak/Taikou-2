# -*- coding: utf-8 -*-
"""gen_oid_map.py —— 把族谱 124 人解析到 BSDATA(officers.json) 的真实 oid。

分级(置信度从高到低):
  exact         姓+名精确命中
  alias         手设别名(名字形态差异的史实人物)命中
  unique_given  名在 700 库里唯一命中          —— 夫人/女儿常"无姓记录 + 名唯一"(阿市/茶茶/初/江),
                                                 这档正是接母系的那一档, 不许删
  fuzzy         名互为子串/共享字符的最近候选(标 ambiguous, 需人工复核)
  none          游戏真无档案 -> 详情走纯 tree_data 自绘 / 未来须合成 BSDATA 记录

前置: officers.json 的占位名先按 BSDATA 内联纠正 (见 sync_names) —— 不纠正会把确有其人的人判成 none。

产物 _tree_oid_map.json: 每 tree 人 -> {oid, conf, officer 关键档案, amb=[候选]}.
"""
import json, os, re, unicodedata
import tree_data as td

OFF = json.load(open(r'F:\Games\Taikou 2\data\officers.json', encoding='utf-8'))

def norm(s):
    return unicodedata.normalize('NFKC', (s or '')).strip()


# BSDATA 内联名才是唯一权威 (记录 +0..6=姓 / +7..13=名, GBK)。
# officers.json 是 modkit 解出来的, 对尾部扩展记录填的是占位名 "姓NNNN/名NNNN" —— 实测 oid695..699
# (柴田胜政/阿市/浅井茶茶/浅井初/浅井江) 全中, 于是这些**游戏里确有其人**的角色被判成"无档案"。
# 母系覆盖 0/49 的头号真因就在这: 不是引擎没有这些女性, 是名字压根没读出来。
BSDATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'BSDATA1.TR2')


def bsd_inline_names():
    raw = open(BSDATA, 'rb').read()
    out = {}
    for k in range(len(raw) // 59):
        r = raw[k * 59:(k + 1) * 59]
        out[k] = (r[0:7].split(b'\x00')[0].decode('gbk', 'replace').strip(),
                  r[7:14].split(b'\x00')[0].decode('gbk', 'replace').strip())
    return out


def sync_names(officers):
    """只把 officers.json 的**占位名**(`姓NNNN`/`名NNNN`)换成 BSDATA 内联名, 返回纠正记录。

    不是无条件覆写: 生僻字那批 (oid182 垪和氏续 / 557,568,581,583 長宗我部·香宗我部) 的内联字节用
    游戏自有码页, GBK 解出来是 U+FFFD —— modkit 的解码反而对, 无条件覆写会把 5 条好名字改坏。
    """
    names, fixed = bsd_inline_names(), []
    ph = re.compile(r'^(姓|名)\d+$')
    for r in officers:
        cur = (norm(r.get('surname')), norm(r.get('given')))
        if not any(ph.match(x) for x in cur):
            continue                        # 不是占位名 => 原样保留
        s, g = names.get(r['bushou_id'], ('', ''))
        if not (s or g) or '\ufffd' in s + g:
            continue                        # 内联也拿不到干净名字 => 留给上层判"无档案"
        fixed.append((r['bushou_id'], ''.join(cur), s + g))
        r['surname'], r['given'] = s, g
    return fixed

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

NAME_FIXES = sync_names(OFF)

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


def _fix_birth(by):
    """BSDATA 生年字节带 0x80 标志位(疑似"已故/未登场"), modkit 解码器把它当成
    年偏移一并加进 birth_year -> 命中该位的记录生年虚高 +128(如森长可 1686=1558+128、
    森兰丸 1693=1565+128)。实测正常记录 1493..1627、被污染记录 1643..1710, 中间
    [1628,1643) 是空档, 故以 1630 为阈值减回 128 即可无损还原真实生年。"""
    if isinstance(by, int) and by >= 1630:
        return by - 128
    return by


def brief(r):
    if not r:
        return {}
    f = r.get('forces', {})
    return {
        'name': r.get('surname', '') + r.get('given', ''),
        'birth_year': _fix_birth(r.get('birth_year')),
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
    print('officers.json 名字被 BSDATA 内联纠正 %d 条: %s' % (len(NAME_FIXES), NAME_FIXES))
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
