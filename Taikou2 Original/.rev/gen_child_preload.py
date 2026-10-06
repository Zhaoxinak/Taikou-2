# -*- coding: utf-8 -*-
"""
gen_child_preload.py —— 生成「开局预载名单」 -> .rev/_child_preload.json

数据源(全静态, 不启动游戏):
  BSDATA{1,2}.TR2.orig  59B×700 记录; 偏移 0x27 的 u16: bits0..6 = 生年-1490, bits7..12 = 登场年-1560
  SNDATA{1,2}.TR2       偏移 0x14 起 700 字节 = 该剧本「已登场标志」(1=开局已在场)
  _tree_oid_map.json    族谱 -> BSDATA oid (只信 conf=exact/alias)

已实测基线(2026-10-05): 剧本1 起始年 = 1560; 在场 354 / 未登场 346 = 已出生 280 + 未出生 66;
已出生里 <15 岁 = 117 人。
本剧本「起始年」是推算的: 用 (已出生=280, 儿童=117) 反解, 唯一解 1560。

批次(batch 名写进 json, build_big 4j 按 BATCH 常量取用):
  fam13   = 族谱可确切对上档案的未登场儿童 —— 恰 13 人(织田信雄…武田胜赖), M2 v1 用这批
  kids117 = 全部已出生未登场儿童(<15)
  all280  = 全部已出生未登场 (**名存实亡**: 本作这 280 条里有 1 条 BSDATA 删除占位记录
            「那个人削除」(oid 466, 国/城都 0xff) ⇒ 已剔除, 真人 279; 且其中 172 人开局已 >=15 虚岁,
            整批预载等于首月批量元服 —— 放量前先读 preview_batch.py 的预演结论)
槽位: 一律从 SLOT_BASE 起顺序排, 且 **绝不占用 0..369(存档区) 与 354..369(4i 待登场武装区)**;
默认 SLOT_BASE=463 = 紧跟 P3b 休眠名预填区(371..462) 之后, 不冲掉任何既有数据。
"""
import json, os, struct, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = r'F:\Games\Taikou 2\Taikou2 Original'
REV = os.path.join(ROOT, '.rev')
R, NREC = 59, 700
START_YEAR = {1: 1560, 2: 1560}      # 剧本起始年(反解所得, 见文件头)
GENPUKU_AGE = 15                     # 儿童判定阈值: age(周岁) < 15
# 注: 引擎 getter 0x49A5C0 报的是**虚岁** = 年-生年+1。按周岁<15 筛 ⇒ 虚岁最大到 15 也会被收进来
# (fam13 的武田胜赖就是这样: 周岁14/虚岁15)。这是故意的 —— 到龄者正好是 M4「到龄自动元服」的样本,
# 成长桩对他走 GROWTH_FREEZE 分支, 一分不涨。别把两套口径混在一张表里, 故条目同时带 age 与 age_engine。
SLOT_BASE = 463                      # 预载槽起点 (371..462 = P3b 休眠名区, 不动)
NATIVE_N = 370                       # 0..369 = 存档区, 预载器禁止侵入

BATCHES = ('fam13', 'kids117', 'all280')


def s7(buf, off):
    return buf[off:off + 7].split(b'\0')[0].decode('gbk', 'replace')


def load_scenario(no):
    """-> [(oid, name, birth, appear_year, in_scenario)] 取 .orig = 原剧本口径(登场年未被 MOD 改过)"""
    bp = os.path.join(ROOT, 'BSDATA%d.TR2.orig' % no)
    sp = os.path.join(ROOT, 'SNDATA%d.TR2' % no)
    d = open(bp, 'rb').read()
    assert len(d) == R * NREC, (bp, len(d))
    flags = open(sp, 'rb').read()[0x14:0x14 + NREC]
    assert len(flags) == NREC
    out = []
    for oid in range(NREC):
        w = struct.unpack_from('<H', d, oid * R + 0x27)[0]
        out.append({
            'oid': oid,
            'name': s7(d, oid * R) + s7(d, oid * R + 7),
            'birth': 1490 + (w & 0x7F),
            'appear': 1560 + ((w >> 7) & 0x3F),
            'in_scenario': bool(flags[oid]),
        })
    return out


def tree_oids():
    m = json.load(open(os.path.join(REV, '_tree_oid_map.json'), encoding='utf-8'))
    tg = {}
    for e in m:
        if e.get('conf') in ('exact', 'alias') and isinstance(e.get('oid'), int):
            nm = (e['officer'] or {}).get('name') or (e['sur'] + e['giv'])
            tg.setdefault(e['oid'], {'name': nm, 'conf': e['conf'], 'rel': e['rel']})
    return tg


def build(no=1):
    recs, tg, S = load_scenario(no), tree_oids(), START_YEAR[no]
    # BSDATA 里的**删除占位记录**(本作 1 条: oid 466「那个人削除」, 国/城都 0xff) —— 不是真人,
    # 预载进来就违背"生成的人物要实实在在能在游戏里有的", 且它会首月元服成浪人占一个槽。
    junk = {r['oid'] for r in recs if '削除' in r['name']}
    born_out = [r for r in recs if not r['in_scenario'] and r['birth'] <= S and r['oid'] not in junk]
    kids = [r for r in born_out if S - r['birth'] < GENPUKU_AGE]
    fam = [r for r in born_out if r['oid'] in tg and S - r['birth'] < GENPUKU_AGE]
    # 儿童在前(按年龄降序 = 长子长女优先), 同龄按 oid 升序, 保证名单稳定可复现
    key = lambda r: (-(S - r['birth']), r['oid'])
    sel = {'fam13': sorted(fam, key=key), 'kids117': sorted(kids, key=key), 'all280': sorted(born_out, key=key)}
    entries = {}
    for bname in BATCHES:
        lst = []
        for i, r in enumerate(sel[bname]):
            lst.append({'oid': r['oid'], 'slot': SLOT_BASE + i, 'name': r['name'],
                        'birth': r['birth'], 'age': S - r['birth'],
                        # 引擎口径(虚岁): getter 0x49A5C0 = 当前年 - 生年 + 1; 桩里的档位/冻结吃这个
                        'age_engine': S - r['birth'] + 1, 'appear': r['appear'],
                        'tree': tg.get(r['oid'], {}).get('name', ''), 'rel': tg.get(r['oid'], {}).get('rel', '')})
        assert len(lst) <= 0x400 - SLOT_BASE - 2, '批次 %s 超出可用扩展槽' % bname
        for e in lst:
            assert e['slot'] >= NATIVE_N, '预载槽不得落进存档区'
        entries[bname] = lst
    meta = {'scenario': no, 'start_year': S, 'genpuku_age': GENPUKU_AGE, 'slot_base': SLOT_BASE,
            'live_in_scenario': sum(1 for r in recs if r['in_scenario']),
            'unappeared': sum(1 for r in recs if not r['in_scenario']),
            'born_unappeared': len(born_out), 'children': len(kids), 'family_children': len(fam),
            'junk_excluded': sorted(junk)}
    return meta, entries


def main():
    meta, entries = build(1)
    print('基数核对: 在场 %(live_in_scenario)d / 未登场 %(unappeared)d / 已出生未登场 %(born_unappeared)d'
          '(已剔删除占位记录 %(junk_excluded)s) / 儿童 %(children)d / 族谱儿童 %(family_children)d'
          % meta)
    assert (meta['live_in_scenario'], meta['born_unappeared'], meta['children']) == (354, 279, 117), \
        '起始年或记录解析与既有实测基数不符(280 减 1 条占位 = 279), 先查数据再谈预载'
    path = os.path.join(REV, '_child_preload.json')
    json.dump({'meta': meta, 'batches': entries}, open(path, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('-> %s' % path)
    for bname in BATCHES:
        lst = entries[bname]
        print('\n[%s] %d 人, 槽 %d..%d' % (bname, len(lst), lst[0]['slot'], lst[-1]['slot']))
        for e in lst[:16]:
            print('   slot %-4d oid %-4d %-10s 生%d 龄%-3d 原生登场年%d %s' %
                  (e['slot'], e['oid'], e['name'], e['birth'], e['age'], e['appear'],
                   ('族谱:' + e['rel']) if e['rel'] else ''))
        if len(lst) > 16:
            print('   ... 余 %d 人' % (len(lst) - 16))


if __name__ == '__main__':
    main()
