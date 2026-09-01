#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SNDATA S8 / S9 / S10 / S16 = MSGX 文本 ID 表（台词・说明文索引）✅ 续102

判定依据：把每段的 WORD 当 MSGX 文本 ID 去 msgx_all_texts.json 反查，
命中率 100%（S16 为 16/20，末 4 项是 0xffff 空槽）—— 不可能是巧合。

  S8  30 × 12B @0x517850  W0=会話セリフ(1000..1029)  W1=商店セリフ(700..729)
  S9  20 × 4B  @0x519238  W0=谋略/訪問セリフ(2000..2019)  W1=商店セリフ(696..699)
  S10 30 × 4B  @0x5176a8  W0=会話セリフ(3000..3029)  W1=0xffff(未用)
  S16 20 × WORD @0x519680 前 8 = 能力/技能説明，后 8 = 对话，末 4 = 0xffff

字段布局（均由各序列化器反汇编坐实）：
  S8  0x47ebb0: esi=0x517852, ebx=0x1e, add esi,0xc
        [esi-2]W +0x00 | [esi+0]W +0x02 | [esi+2]B +0x04 | [esi+3]B +0x05
        [esi+4]B +0x06 | [esi+5]B +0x07 | [esi+6]W +0x08 | [esi+8]B +0x0a | [esi+9]B +0x0b
  S9  0x47ecb0: esi=0x51923a, ebx=0x14, add esi,4  -> [esi-2]W +0x00 | [esi+0]W +0x02
  S10 0x47ed10: esi=0x5176aa, ebx=0x1e, add esi,4  -> [esi-2]W +0x00 | [esi+0]W +0x02
  S16 0x47f1b0: esi=0x519680, edi=0x14, add esi,2  -> 20 × WORD
"""
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

import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STREAM_BASE = 0x58C
LENS = [22, 21830, 5200, 245, 539, 180, 46, 3200, 360, 80,
        120, 3800, 160, 2280, 1176, 25, 40, 133]
ABILITY_ORDER = '体力 内政 外交 茶道 剣術 作戦 忍術 兵力'.split()


def u16(b, i):
    return b[i] | (b[i + 1] << 8)


def decode(fn):
    data = open(os.path.join(ROOT, fn), 'rb').read()
    key = data[0x12] ^ data[0x13]
    return bytes(x ^ key for x in data[STREAM_BASE:])


def bounds():
    out, c = [], 0
    for L in LENS:
        out.append((c, c + L)); c += L
    return out


def main():
    ok = fail = 0
    def chk(l, cond):
        nonlocal ok, fail
        if cond: ok += 1; print(f'  [PASS] {l}')
        else:    fail += 1; print(f'  [FAIL] {l}')

    T = json.load(open(os.path.join(ROOT, _ROOT + '/scripts/msgx_all_texts.json'),
                       encoding='utf-8'))['texts']
    g = lambda i: T.get(str(i), T.get(i))
    B = bounds()
    result = {}
    S16_BY_SC = {}

    for sc, fn in (('scenario1', _ROOT + '/Taikou2 Original/SNDATA1.TR2'),
                   ('scenario2', _ROOT + '/Taikou2 Original/SNDATA2.TR2')):
        s = decode(fn)
        S = [s[a:e] for a, e in B]
        print(f'\n--- {sc} ---')
        # S8
        d = S[8]
        pairs = [(u16(d, 12 * k), u16(d, 12 * k + 2)) for k in range(30)]
        chk('S8 W0 = MSGX 1000..1029 连续', [p[0] for p in pairs] == list(range(1000, 1030)))
        chk('S8 W0 全部命中 MSGX (30/30)', all(g(p[0]) for p in pairs))
        # 实为 700..728 共 29 条 + 1 个 0xffff 哨兵（末槽空）
        chk('S8 W1 = 700..728 连续 + 末槽 0xffff',
            [p[1] for p in pairs][:29] == list(range(700, 729)) and pairs[29][1] == 0xffff)
        chk('S8 W1 前 29 条全部命中 MSGX', all(g(p[1]) for p in pairs[:29]))
        # S9
        d = S[9]
        p9 = [(u16(d, 4 * k), u16(d, 4 * k + 2)) for k in range(20)]
        chk('S9 W0 = MSGX 2000..2019 连续', [p[0] for p in p9] == list(range(2000, 2020)))
        chk('S9 W0 全部命中 MSGX (20/20)', all(g(p[0]) for p in p9))
        chk('S9 W1 ∈ 696..699 且全部命中', all(696 <= p[1] <= 699 and g(p[1]) for p in p9))
        # S10
        d = S[10]
        p10 = [(u16(d, 4 * k), u16(d, 4 * k + 2)) for k in range(30)]
        chk('S10 W0 = MSGX 3000..3029 连续', [p[0] for p in p10] == list(range(3000, 3030)))
        chk('S10 W0 全部命中 MSGX (30/30)', all(g(p[0]) for p in p10))
        chk('S10 W1 恒 0xffff', all(p[1] == 0xffff for p in p10))
        # S16
        d = S[16]
        w16 = [u16(d, 2 * k) for k in range(20)]
        # 前 8 项（能力説明）双剧本恒定；8..19 槽随剧本变化（可含 0xffff 空槽）
        chk('S16 前 8 项 = 8 能力説明 MSGX（集合 = {1,4,5,11,12,13,15,18}）',
            set(w16[:8]) == {1, 4, 5, 11, 12, 13, 15, 18})
        chk('S16 前 8 项全部命中 MSGX', all(g(w) for w in w16[:8]))
        chk('S16 非空槽全部命中 MSGX',
            all(w == 0xffff or g(w) for w in w16))
        S16_BY_SC[sc] = w16

        if sc == 'scenario1':
            d8 = S[8]
            result = {
                'S8_dialogue_30x12B': [
                    {'idx': k, 'talk_id': u16(d8, 12 * k), 'talk': g(u16(d8, 12 * k)),
                     'shop_id': u16(d8, 12 * k + 2), 'shop': g(u16(d8, 12 * k + 2)),
                     'b4': d8[12 * k + 4], 'b5': d8[12 * k + 5],
                     'b6': d8[12 * k + 6], 'b7': d8[12 * k + 7],
                     'w8': u16(d8, 12 * k + 8), 'ba': d8[12 * k + 10], 'bb': d8[12 * k + 11]}
                    for k in range(30)],
                'S9_dialogue_20x4B': [
                    {'idx': k, 'talk_id': p9[k][0], 'talk': g(p9[k][0]),
                     'shop_id': p9[k][1], 'shop': g(p9[k][1])} for k in range(20)],
                'S10_dialogue_30x4B': [
                    {'idx': k, 'talk_id': p10[k][0], 'talk': g(p10[k][0])}
                    for k in range(30)],
                'S16_textids_20': [
                    {'idx': k, 'msgx': w16[k],
                     'text': g(w16[k]) if w16[k] != 0xffff else None,
                     'ability': ABILITY_ORDER[k] if k < 8 else None}
                    for k in range(20)],
            }
    chk('S16 前 8 项在两剧本间完全相同（静态能力説明）',
        S16_BY_SC['scenario1'][:8] == S16_BY_SC['scenario2'][:8])
    result['S16_scenario2'] = [
        {'idx': k, 'msgx': S16_BY_SC['scenario2'][k],
         'text': g(S16_BY_SC['scenario2'][k]) if S16_BY_SC['scenario2'][k] != 0xffff else None}
        for k in range(20)]
    json.dump(result, open(os.path.join(ROOT, _ROOT + '/scripts/msgx_text_tables.json'),
                           'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n==== {ok} PASS / {fail} FAIL ====')
    print('saved scripts/msgx_text_tables.json')
    return 0 if fail == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
