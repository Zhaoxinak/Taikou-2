# -*- coding: utf-8 -*-
"""gen_kin.py —— M3a 亲子索引 + 随父居住落点表 -> .rev/_kin.json

三件事:
  1) **oid2slot**: 原生池 370 槽里「哪个 oid 住在哪个槽」。BSDATA 的家系链接给的是 **oid**,
     而 child_stub 的排程表要的是**槽** —— 这一层翻译就是亲子索引的本体。
     来源 = SNDATA 解密流的 S1 段(370×59B), rec[+0x10]=oid。
     真机对账(ents_dump.json, 本脚本 main 里重跑): rec[0x10]==实体+0x02 370/370;
     rec[0x30]/[0x31]==实体+0x24/+0x25(国/城) 370/370; 空槽恰是 354..369(=4i 待登场区)。
  2) **每个预载孩子的父 + 静态兜底城**:
     父亲先取 BSDATA 原生链接 rec[+0x29](156 条真链接; 与实体 word+0x1d 逐槽吻合, 引擎自己就认它),
     无链接时退取族谱父子边(_tree_oid_map conf=exact/alias 落到 oid)。
     fslot 有效 ⇒ 运行时读父亲实体的现城(动态); 兜底城 = 父亲的 S1 国/城;
     父不在原生池 ⇒ 父亲的 BSDATA 国/城; 连父都不明 ⇒ 孩子自己的 BSDATA 国/城(INST 原值, 等于不写)。
  3) **母亲**: 族谱里挂在该父亲节点上的配偶节点(tree_data v9 约定) ⇒ M3b/M3c 双亲教学要用;
     族谱一部只记一位正室, 所以母亲是「养母口径」, 字段里如实标 mother_src。

输出只给构建期用(build_big 4j 打包成 8B 排程表; verify_children C15 独立复核), 不进 exe。
"""
import json
import os
import struct
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = r'F:\Games\Taikou 2\Taikou2 Original'
REV = os.path.join(ROOT, '.rev')
R, NREC, NAT = 59, 700, 370
TERM = 0xFFFF
NATIVE_N = 370                      # 0..369 = 存档区

STREAM_BASE = 0x598                 # SNDATA XOR 单字节加密流起点 (key = byte[0x12]^byte[0x13])
S1_STREAM_OFF = 0x0A                # S1 = 流首 10B 头之后的 370×59B 实体池初值 (绝对 0x5A2)
S1_OID = 0x10                       # rec[+0x10] = BSDATA oid (空槽 0xffff)
S1_PV, S1_CITY = 0x30, 0x31         # rec[+0x30]=国 / +0x31=城  ->  实体 +0x24 / +0x25
BS_FATHER, BS_PV, BS_CITY = 0x29, 0x30, 0x31     # 父 = **u16** LE (0xffff=无); 国/城 是单字节
ENT_OID, ENT_FATHER = 0x02, 0x1d    # 实体里的 oid / 父 oid


def s7(b, o):
    return b[o:o + 7].split(b'\0')[0].decode('gbk', 'replace')


def u16(b, o):
    return struct.unpack_from('<H', b, o)[0]


def bsd(no=1):
    p = os.path.join(ROOT, 'BSDATA%d.TR2.orig' % no)
    d = open(p, 'rb').read()
    assert len(d) == R * NREC, (p, len(d))
    return d


def s1_records(no=1):
    d = open(os.path.join(ROOT, 'SNDATA%d.TR2' % no), 'rb').read()
    key = d[0x12] ^ d[0x13]
    st = bytes(c ^ key for c in d[STREAM_BASE:])
    seg = st[S1_STREAM_OFF:S1_STREAM_OFF + R * NAT]
    assert len(seg) == R * NAT, '流太短, S1 不完整'
    return [seg[i * R:(i + 1) * R] for i in range(NAT)]


def name_of(d, oid):
    return s7(d, oid * R) + s7(d, oid * R + 7)


# ---------------- 族谱 -> 父子边 ----------------
def tree_edges():
    """-> {child_oid: {'father': oid|None, 'mother': oid|None, 'fam': 家族标题, 'rel': 关系}}

    tree_data 约定: 节点 = (父索引|None, 姓, 名, 关系, 状态[, 是配偶]);
    配偶节点的 parent = **丈夫索引**。所以孩子的父索引既可能是父亲本人, 也可能是母亲(配偶节点)。
    同一人会在多家出现(信长在柴田/浅井/织田三棵树里都有), 只采纳「有父链接」的那条边,
    并优先父姓与本家姓一致的那棵(父系本家); 仍有分歧就如实记 conflict 并放弃族谱父。
    """
    import tree_data as TD
    mmap = {}
    for e in json.load(open(os.path.join(REV, '_tree_oid_map.json'), encoding='utf-8')):
        if e.get('conf') in ('exact', 'alias') and isinstance(e.get('oid'), int):
            mmap[(e['sur'], e['giv'])] = e['oid']

    def oid_of(nd):
        return mmap.get((nd[1], nd[2]))

    cand = {}
    for (title, trigs, subject, nodes) in TD.TREES:
        spouse_of = {nd[0]: i for i, nd in enumerate(nodes) if len(nd) > 5 and bool(nd[5])}
        husband_of = {v: k for k, v in spouse_of.items()}
        for i, nd in enumerate(nodes):
            if len(nd) > 5 and bool(nd[5]):
                continue                                   # 配偶节点自己不是检索对象
            co = oid_of(nd)
            p = nd[0]
            if co is None or p is None:
                continue
            pn = nodes[p]
            if p in husband_of:                              # 母(配偶节点)下挂的孩子
                mo, fo = oid_of(pn), husband_of[p]
                fa = oid_of(nodes[fo]) if fo is not None else None
                msrc = 'tree_wife'
            else:
                fa = oid_of(pn)
                w = spouse_of.get(p)
                mo = oid_of(nodes[w]) if w is not None else None
                msrc = 'tree_spouse_of_father' if w is not None else None
            home = (nd[1] == title or nd[1] == '')           # 在本家姓的树里出现的边更可信
            cand.setdefault(co, []).append(
                {'father': fa, 'mother': mo, 'fam': title, 'rel': nd[3], 'home': home,
                 'mother_src': msrc})
    out = {}
    for co, lst in cand.items():
        def pick(field):
            vals = {e[field] for e in lst if e[field] is not None}
            if len(vals) == 1:
                return vals.pop(), False
            if not vals:
                return None, False
            hm = {e[field] for e in lst if e['home'] and e[field] is not None}
            if len(hm) == 1:
                return hm.pop(), True
            return None, True
        fa, fambig = pick('father')
        mo, mombig = pick('mother')
        src = next((e['mother_src'] for e in lst if e['mother'] == mo and e['mother_src']), None)
        out[co] = {'father': fa, 'mother': mo,
                   'fam': '/'.join(sorted({e['fam'] for e in lst})),
                   'rel': '/'.join(sorted({e['rel'] for e in lst})),
                   'mother_src': src,
                   'conflict': 'father' if fambig else ('mother' if mombig else '')}
    return out


# ---------------- 主构造 ----------------
def build(no=1):
    D = bsd(no)
    recs = s1_records(no)
    oid2slot = {}
    for slot, rr in enumerate(recs):
        o = u16(rr, S1_OID)
        if o != TERM:
            oid2slot[o] = slot
    edges = tree_edges()
    pre = json.load(open(os.path.join(REV, '_child_preload.json'), encoding='utf-8'))
    S = pre['meta']['start_year']

    # 国 -> **众数城**: BSDATA 的城字段有 156 条是 0xff(未设定), 落 0xff 城 = 这人不属于任何城
    #   => 培养面板的"同城筛"永远筛不到他(玩法死), 挂载 0x4A5100 的门也要求 城<0xc8。
    #   数据源用 S1 在场 354 人的 国/城(与真机逐槽吻合, 见 selfcheck_dump 的 pv_city), 平票取城号小者 => 可复现。
    tally = {}
    for rr in recs:
        if u16(rr, S1_OID) == TERM:
            continue
        g, c = rr[S1_PV], rr[S1_CITY]
        if g < 0x31 and c < 0xc8:
            row = tally.setdefault(g, {})
            row[c] = row.get(c, 0) + 1
    guo_city = {g: min(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[0] for g, cnt in tally.items()}

    def fstatic(fo):
        """父的兜底国/城: 在原生池用他的 S1 剧本值, 不在池用他的 BSDATA 值"""
        if fo in oid2slot:
            rr = recs[oid2slot[fo]]
            return rr[S1_PV], rr[S1_CITY], 's1'
        return D[fo * R + BS_PV], D[fo * R + BS_CITY], 'bsd'

    def resolve(e):
        oid = e['oid']
        fb = u16(D, oid * R + BS_FATHER)
        f_bsd = None if fb == TERM else fb
        ed = edges.get(oid, {})
        f_tree = ed.get('father')
        # 引擎自己认 BSDATA 那条链接(它会被 INST 抄进实体 word+0x1d), 族谱只补空白
        conflict = (f_bsd is not None and f_tree is not None and f_bsd != f_tree)
        father = f_bsd if f_bsd is not None else f_tree
        fsrc = ('bsd' if f_bsd is not None else 'tree') if father is not None else 'none'
        fslot = oid2slot.get(father, TERM) if father is not None else TERM
        if father is not None:
            pv, city, pvs = fstatic(father)
        else:                                   # 不明其父: 用他自己的 BSDATA 落点(INST 原值, 等于不写)
            pv, city, pvs = D[oid * R + BS_PV], D[oid * R + BS_CITY], 'self'
        if city == 0xFF:                          # 城字段"未设定" => 落他**本国的众数城**(S1 在场者多数城)
            g = pv if pv in guo_city else D[oid * R + BS_PV]
            if g in guo_city:
                pv, city, pvs = g, guo_city[g], 'guo'
        mo = ed.get('mother')
        return {'oid': oid, 'name': e['name'], 'age': e['age'],
                'age_engine': e.get('age_engine', e['age'] + 1),
                'self_pv': D[oid * R + BS_PV], 'self_city': D[oid * R + BS_CITY],
                'father_oid': father, 'father_name': name_of(D, father) if father is not None else '',
                'father_src': fsrc, 'father_bsd': f_bsd, 'father_tree': f_tree,
                'fslot': fslot, 'pv': pv, 'city': city, 'pv_src': pvs, 'dyn': fslot != TERM,
                'mother_oid': mo, 'mother_name': name_of(D, mo) if mo is not None else '',
                'mother_src': ed.get('mother_src', ''),
                # mslot 只查**原生池**(oid2slot 恒为 354 项, C12b 按这个口径对账)。
                # 母亲自己就是预载儿童时(如 阿市 oid696)这里必然是 0xffff, 真槽号要按批次查
                # batches[batch] 的 [oid,slot] 表 —— 排程表 8B/条暂无母槽位, M3b-3/M4 要用再加。
                'mslot': oid2slot.get(mo, TERM) if mo is not None else TERM,
                'tree_fam': ed.get('fam', ''), 'tree_rel': ed.get('rel', ''),
                'tree_conflict': ('father' if conflict else ed.get('conflict', ''))}

    # 同一孩子会出现在多个批次, 而**每批都从 SLOT_BASE 重排槽位** ⇒ 槽是批次属性, 不进 kin
    kin = {}
    batches = {}
    for batch, lst in pre['batches'].items():
        rows = []
        for e in lst:
            r = kin.get(e['oid'])
            if r is None:
                r = kin[e['oid']] = resolve(e)
            rows.append(dict(r, slot=e['slot']))
        batches[batch] = rows

    allrows = list(kin.values())
    cnt = lambda f, sub=None: sum(1 for r in (sub if sub is not None else allrows) if f(r))
    meta = {'scenario': no, 'start_year': S, 'stream_base': STREAM_BASE, 's1_stream_off': S1_STREAM_OFF,
            's1_file_off': STREAM_BASE + S1_STREAM_OFF, 'entry_size': 8,
            'pool_native': NAT, 'natives': len(oid2slot),
            'empty_slots': [i for i in range(NAT) if u16(recs[i], S1_OID) == TERM],
            'tree_edges': len(edges), 'children': len(allrows),
            'with_father': cnt(lambda r: r['father_oid'] is not None),
            'father_bsd': cnt(lambda r: r['father_src'] == 'bsd'),
            'father_tree': cnt(lambda r: r['father_src'] == 'tree'),
            'dyn_slot': cnt(lambda r: r['dyn']),
            'static_only': cnt(lambda r: not r['dyn']),
            'self_home': cnt(lambda r: r['pv_src'] == 'self'),
            'home_by_guo': cnt(lambda r: r['pv_src'] == 'guo'),
            'no_home_left': cnt(lambda r: r['city'] == 0xFF),
            'with_mother': cnt(lambda r: r['mother_oid'] is not None),
            'conflict': cnt(lambda r: r['tree_conflict'])}
    return meta, oid2slot, batches, kin, recs


def selfcheck_dump(recs, D):
    """用真机 ents_dump 复核 S1 的三条位移常量 + 「父 = 记录 u16@+0x29」这条读法(文件不在则跳过)"""
    p = os.path.join(REV, 'ents_dump.json')
    if not os.path.exists(p):
        return None
    E = json.load(open(p, encoding='utf-8'))
    assert len(E) == NAT, len(E)
    a = b = c = d = noid = 0
    for i, e in enumerate(E):
        raw = bytes.fromhex(e['raw'])
        oid = u16(raw, ENT_OID)
        a += u16(raw, ENT_OID) == u16(recs[i], S1_OID)
        b += raw[0x24] == recs[i][S1_PV] and raw[0x25] == recs[i][S1_CITY]
        c += u16(raw, ENT_FATHER) == e['father']
        if oid != TERM:
            noid += 1
            d += u16(D, oid * R + BS_FATHER) == u16(raw, ENT_FATHER)
    return {'oid': '%d/%d' % (a, NAT), 'pv_city': '%d/%d' % (b, NAT),
            'father_ent': '%d/%d' % (c, NAT), 'father_bsd_u16': '%d/%d' % (d, noid)}


def main():
    meta, oid2slot, batches, kin, recs = build(1)
    D = bsd(1)
    chk = selfcheck_dump(recs, D)
    print('S1/父字段 对账(真机 ents_dump): %s' % chk)
    if chk:
        assert chk['oid'] == '370/370' and chk['pv_city'] == '370/370', chk
        assert chk['father_ent'] == '370/370' and chk['father_bsd_u16'] == '354/354', chk
    # 族谱父 与 BSDATA 父 的一致率(族谱里有养子/叔侄, 少量不符是正常的; 大面积不符=读法错了)
    edges = tree_edges()
    pair = [(c, v['father']) for c, v in edges.items() if v['father'] is not None]
    agree = sum(1 for c, f in pair if u16(D, c * R + BS_FATHER) == f)
    print('原生池 oid %d 个 / 空槽 %s' % (meta['natives'], meta['empty_slots'][:4]))
    assert meta['natives'] == 354 and meta['empty_slots'] == list(range(354, 370))
    print('族谱父子边 %d 条(有父 %d) / 待解孩子 %d 人 / 族谱父~BSDATA 父 一致 %d/%d'
          % (meta['tree_edges'], len(pair), meta['children'], agree, len(pair)))
    assert len(pair) >= 20 and agree >= len(pair) * 0.8, ('父字段读法可疑', agree, len(pair))
    print('\n批次  人数  有父  bsd/tree  父在池  兜底=自身  有母  冲突')
    for b, rows in batches.items():
        print('%-7s %4d %5d %6d/%-5d %6d %8d %5d %5d' % (
            b, len(rows),
            sum(1 for r in rows if r['father_oid'] is not None),
            sum(1 for r in rows if r['father_src'] == 'bsd'),
            sum(1 for r in rows if r['father_src'] == 'tree'),
            sum(1 for r in rows if r['dyn']),
            sum(1 for r in rows if r['pv_src'] == 'self'),
            sum(1 for r in rows if r['mother_oid'] is not None),
            sum(1 for r in rows if r['tree_conflict'])))
    print('\n[fam13] 明细 (国/城 = **父亲**的落点; dyn = 运行时跟父亲现城走; 龄 = 引擎虚岁 年-生年+1)')
    for r in batches['fam13']:
        print('  槽%-4d oid%-4d %-8s 龄%-3d 父=%-8s(%-4s) fslot=%-5s 国%-3d 城%-3d <-%-4s 母=%s' % (
            r['slot'], r['oid'], r['name'], r['age_engine'], r['father_name'] or '-', r['father_src'],
            r['fslot'] if r['dyn'] else '-', r['pv'], r['city'], r['pv_src'], r['mother_name'] or '-'))
    for oid, r in sorted(kin.items()):
        if r['tree_conflict']:
            print('  ! oid%-4d %-8s %s: BSDATA 父=%-8s(%s) 族谱父=%-8s(%s) -> 采 %s'
                  % (oid, r['name'], r['tree_conflict'],
                     name_of(D, r['father_bsd']) if r['father_bsd'] is not None else '-', r['father_bsd'],
                     name_of(D, r['father_tree']) if r['father_tree'] is not None else '-', r['father_tree'],
                     r['father_oid']))
    out = os.path.join(REV, '_kin.json')
    json.dump({'meta': meta, 'oid2slot': {str(k): v for k, v in sorted(oid2slot.items())},
               'batches': {b: [[r['oid'], r['slot']] for r in rows] for b, rows in batches.items()},
               'kin': {str(k): v for k, v in sorted(kin.items())}},
              open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('\n-> %s' % out)


if __name__ == '__main__':
    main()
