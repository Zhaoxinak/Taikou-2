# -*- coding: utf-8 -*-
"""preview_batch.py —— 放量(kids117/all280)前的**纸面预演** (纯静态, 不读也不改 exe, 不启动游戏)

为什么要它: `verify_children.py` 验的是**已经建进 big.exe 的那一批**(要吃 exe 字节), 而冒烟阶梯
13 -> 117 -> 280 的规矩是"上一批还没实机过就别换批次"。本脚本只吃三张 json
(`_child_preload.json` 名单 / `_kin.json` 亲子与落点 / `ents_dump.json` 真机 354 在场实体),
把后两批**会撞的墙提前数出来**, 结论直接决定下一次 `CHILD_BATCH=` 该不该抬。

看六件事 (全部有出处, 不是估的):
  1 槽区间     : 不得侵入 0..369(存档区) / 354..369(4i 待登场武装区) / 371..462(P3b 休眠名区),
                 且条目数不得超排程表容量 = (CHILD_PASS - CHILD_SCHED)/ESZ - 1 (最后一条是 0xFFFF 哨兵)
  2 随父居住   : 父亲在原生池且 bit15=0 => 每月动态跟父; 否则退静态城; fslot=ffff => 无父
  3 面板分页   : 培养面板只列**本城**孩子; 原生 0x47BED0 一屏硬上界 = menu.item_max(12), 超了**连窗口都不建**
                 => 一级「选孩子」已改成分页(每页 PAGE_KIDS 个 + 尾追 下一页/上一页, 总行数恒 <=12),
                    所以同城孩子 >12 不再是"选不到", 这里只数"要翻几页 / 单城孩子数是否离谱"
  4 元服时间线 : puku_month 用 child_growth 里那条与桩同源的换算; 首月人数 = CHILD_GENPUKU 首期望,
                 最大单月 = 同月批量挂载的冲击, Σ(元服月-1) = GROWTH_SETTLED 上界
  5 归属存疑   : 无父者走 0x4A5290(本国国主/浪人); 族谱里 rel 是 母/正室/女/妹/儿媳/休室 的
                 = 女性节点, 让她们元服成 家臣 属语义可疑项, 交给用户拍板
  6 成人出路   : 本批里虚岁已达元服阈值的"成人"有多少, 他们的**原生登场年**落在哪几年, 对
                 4i 待登场队列(仅 reserve_n 槽)意味着什么 —— 决定成人该走原生登场还是儿童预载
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REV = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REV)
import child_growth as CG
import child_menu as CM

J = lambda f: json.load(io.open(os.path.join(REV, f), encoding='utf-8'))
LY = J('_big_layout.json')
PRE = J('_child_preload.json')
KIN = J('_kin.json')
ENTS = J('ents_dump.json')
SCHED_CAP = (LY['v']['CHILD_PASS'] - LY['v']['CHILD_SCHED']) // 8 - 1
ITEM_MAX = LY['menu']['item_max']
RES_LO, RES_N = LY['reserve_lo'], LY['reserve_n']
NAME_FROZEN = 462                 # 371..462 = P3b 休眠名预填区
FEMALE_REL = ('母', '正室', '女', '妹', '儿媳', '休室', '三女', '四女', '长女', '次女', '孙妇')
START_MONTH = int(os.environ.get('TKID_START_MONTH', '1'))


def eng_age(birth):
    return KIN['meta']['start_year'] - birth + 1


def gate_ok(fslot):
    """父亲能否当 0x4A5100 的『主人』: 四道门 = bit15=0 / 身分码!=0 / 城<0xc8 / 国<0x31 (逐条对着 exe 字节)"""
    if not (0 <= fslot < len(ENTS)):
        return False, '父槽号越界'
    e = ENTS[fslot]
    if not e or e.get('slot') != fslot:
        return False, '父槽不在 354 在场表'
    raw = bytes.fromhex(e['raw'])
    w = int.from_bytes(raw[0x2c:0x2e], 'little')
    ok = (not w & 0x8000) and ((w >> 8) & 7) and raw[0x25] < 0xc8 and raw[0x24] < 0x31
    return ok, '' if ok else 'bit15=%d 身分=%d 城=%d 国=%d' % (
        1 if w & 0x8000 else 0, (w >> 8) & 7, raw[0x25], raw[0x24])


def report(bname):
    lst = PRE['batches'][bname]
    kmap = {int(k): v for k, v in KIN['kin'].items()}
    lo, hi = lst[0]['slot'], lst[-1]['slot']
    bad = []
    if lo < NAME_FROZEN + 1:
        bad.append('起点 %d 落进休眠名区/存档区' % lo)
    if any(RES_LO <= s < RES_LO + RES_N for s in range(lo, hi + 1)):
        bad.append('与 4i 待登场槽 %d..%d 重叠' % (RES_LO, RES_LO + RES_N - 1))
    if len(lst) > SCHED_CAP:
        bad.append('条目 %d 超排程表容量 %d' % (len(lst), SCHED_CAP))
    if hi >= LY['cap']:
        bad.append('尾槽 %d 越 CAP %d' % (hi, LY['cap']))

    dyn = stat = none = 0
    by_city, pm, female, orphan, src = {}, {}, [], [], {}
    for e in lst:
        k = kmap[e['oid']]
        fs = k['fslot']
        if fs == 65535:
            none += 1
            orphan.append(e)
        else:
            ok, _ = gate_ok(fs)
            dyn += 1 if ok else 0
            stat += 0 if ok else 1
        src[k['pv_src']] = src.get(k['pv_src'], 0) + 1
        by_city[k['city']] = by_city.get(k['city'], 0) + 1
        m = CG.puku_month(eng_age(e['birth']), START_MONTH, LY['genpuku_age'])
        pm[m] = pm.get(m, 0) + 1
        if (k['tree_rel'] or e.get('rel') or '') in FEMALE_REL:
            female.append(e)

    settled = sum((CG.puku_month(eng_age(x['birth']), START_MONTH, LY['genpuku_age']) - 1) for x in lst)
    peak_m = max(pm, key=lambda m: pm[m])
    print('\n[%s] %d 人, 槽 %d..%d  (排程表容量 %d 条, 用去 %d)' % (bname, len(lst), lo, hi, SCHED_CAP, len(lst)))
    print('  1 槽区间  : %s' % ('全部约束通过' if not bad else ' *** ' + '; '.join(bad)))
    print('  2 随父    : 动态跟父 %d / 父在池但门不过(退静态) %d / 无父 %d   (落城来源 %s)'
          % (dyn, stat, none, ' '.join('%s:%d' % x for x in sorted(src.items()))))
    top = sorted(by_city.items(), key=lambda kv: -kv[1])[:8]
    over = sorted([c for c, n in by_city.items() if n > ITEM_MAX], key=lambda c: -by_city[c])
    _pg = {c: (n + CM.PAGE_KIDS - 1) // CM.PAGE_KIDS for c, n in by_city.items()}
    print('  3 每城孩子: top %s ; 一屏放不下的城 %s' % (
        ' '.join('城%d:%d' % x for x in top),
        ' '.join('城%d:%d人%d页' % (c, by_city[c], _pg[c]) for c in over[:8]) or '无'))
    print('     分页后: 每页 %d 人 + 导航 <=%d 行 (硬门 %d), 最多 %d 页, 全部可选到'
          % (CM.PAGE_KIDS, CM.PAGE_KIDS + 2, ITEM_MAX, max(list(_pg.values()) or [0])))
    print('  4 元服    : 首月 %d 人 ; 最大单月 第%d月 %d 人 ; 最后一人 第%d月 ; GROWTH_SETTLED 上界 %d 人次'
          % (pm.get(1, 0), peak_m, pm[peak_m], max(pm), settled))
    print('     前 24 月累计 %s' % ' '.join('%d:%d' % (m, sum(n for k, n in pm.items() if k <= m))
                                            for m in sorted(set(list(pm) + [1, 6, 12, 18, 24])) if m <= 24))
    print('  5 存疑    : 无父(走国主/浪人) %s ; 女性节点 %d 人 %s'
          % (sorted(x['slot'] for x in orphan)[:12], len(female),
             ' '.join('%s@%d' % (x['name'], x['slot']) for x in female[:10])))

    # 6 成人出路: 成人(虚岁已达元服阈值)走原生登场通道还是要进儿童预载
    sy = KIN['meta']['start_year']
    grown = [e for e in lst if e['age'] >= LY['genpuku_age']]
    _ap = [e['appear'] for e in grown]
    _h = {}
    for a in _ap:
        _h[a] = _h.get(a, 0) + 1
    _bk = [('即开局<=%d' % sy, sum(n for a, n in _h.items() if a <= sy)),
           ('开局次年%d' % (sy + 1), _h.get(sy + 1, 0)),
           ('%d..%d' % (sy + 2, sy + 10), sum(n for a, n in _h.items() if sy + 2 <= a <= sy + 10)),
           ('>%d' % (sy + 10), sum(n for a, n in _h.items() if a > sy + 10))]
    _pk = max(_h, key=lambda a: _h[a]) if _h else 0
    oldest = max(grown, key=lambda e: e['age']) if grown else None
    print('  6 成人出路: 本批成人(虚岁>=%d) %d / 儿童 %d ; 成人的原生登场年 %s'
          % (LY['genpuku_age'], len(grown), len(lst) - len(grown),
             ' '.join('%s:%d' % x for x in _bk)))
    if not grown:
        print('     本批无成人 => 成人出路问题不适用 (首月元服 %d 人都是到龄儿童)' % pm.get(1, 0))
    else:
        print('     4i 待登场队列只有 %d 槽: 峰值年 %d 候选 %d 人 => 要排 %d 轮, 超额者只能等游戏内身故腾槽;'
              % (RES_N, _pk, _h[_pk], (_h[_pk] + RES_N - 1) // RES_N))
        print('     若改走儿童预载: 首月一次挂 %d 发元服(最年长 %s %d 岁) —— 成人被当成儿童养'
              % (pm.get(1, 0), oldest['name'], oldest['age']))
    return bad, len(grown), _h, pm.get(1, 0)


def main():
    print('预演口径: 起始年 %s / 开局日历月 %d (TKID_START_MONTH 可改) / 元服阈值 虚岁>=%d / 面板一屏 %d 项 (每页孩子 %d)'
          % (KIN['meta']['start_year'], START_MONTH, LY['genpuku_age'], ITEM_MAX, CM.PAGE_KIDS))
    print('4i 待登场槽 %d..%d 由原生登场专用, 预载一律从 %d 起' % (
        RES_LO, RES_LO + RES_N - 1, KIN['meta'].get('slot_base') or PRE['meta']['slot_base']))
    hard, grown_n, ap_h, first_mo = {}, {}, {}, {}
    for b in ('fam13', 'kids117', 'all280'):
        hard[b], grown_n[b], ap_h[b], first_mo[b] = report(b)
    print('\n结论: %s' % ('三批都无硬冲突' if not any(hard.values())
                          else '; '.join('%s: %s' % (k, v) for k, v in hard.items() if v)))
    # 坎②: 成人不该进儿童预载 —— 有数可查(登场年取自 _child_preload.json, 队列容量取自 layout)
    sy1 = KIN['meta']['start_year'] + 1
    y1 = ap_h['all280'].get(sy1, 0)
    print('  坎②(成人该不该整批儿童预载) 定论: 不该。all280 比 kids117 多的 %d 名成人里, '
          '原生登场年=%d 的有 %d 人: 走 4i 只有 %d 槽, 相当于要排 %d 轮队(超额者只能等身故腾槽, 事实上到不了场); '
          '走儿童预载则是开局首月一次挂 %d 发元服(= 成人 %d + 已到龄儿童 %d), 成人被当成儿童养。'
          '放量因此取 kids117(真儿童, 首月只 %d 发), 成人留原生登场通道 —— 别把 CHILD_BATCH 抬到 all280。'
          % (grown_n['all280'] - grown_n['kids117'], sy1, y1, RES_N,
             (y1 + RES_N - 1) // RES_N, first_mo['all280'], grown_n['all280'], first_mo['kids117'],
             first_mo['kids117']))


if __name__ == '__main__':
    main()
