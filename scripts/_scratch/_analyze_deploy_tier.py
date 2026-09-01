#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SECT_A tier (row 0..8) ↔ HJMAPDAT deploy ASCII token 共现分析。

部署区 C：40×19 ASCII（见 _extract_hjmapdat.py）。
SECT_A：9×20 nibble 表；row = 内部部署 tier，col = 调参槽。

输出：scripts/deploy_tier_map.json + stdout 摘要（UTF-8）。
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

import json, sys, io, collections, statistics as st

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BATTLES = 'hjmapdat_battles.json'
OUT = _ROOT + '/scripts/deploy_tier_map.json'

# 语义分组（deployment_tactics_ref / _extract_hjmapdat DEPLOY_NAMES）
WINGS = {
    'left': set('JKI/1'),
    'center': set('+H3-'),
    'right': set('98275'),
}
TOKEN_LABEL = {
    'J': 'left_general', 'K': 'left_troop', 'I': 'left_wing',
    '/': 'left_special', '1': 'left_marker',
    '+': 'center', 'H': 'center_troop', '3': 'center_general', '-': 'center_reserve',
    '9': 'right_general', '8': 'right_troop', '2': 'right_wing',
    '7': 'right_marker', '5': 'right_special',
}


def row_populated(unit_row):
    return sum(1 for n in unit_row['nibbles'] if n > 0)


def main():
    battles = json.load(open(BATTLES, encoding='utf-8'))
    deploy_chars = collections.Counter()
    for b in battles:
        for row in b['deploy']:
            for ch in row:
                if ch not in ' \x00':
                    deploy_chars[ch] += 1

    # token vs tier: when tier r has pop>threshold, token t frequency in that battle
    tier_token = {r: collections.Counter() for r in range(9)}
    tier_pop = {r: [] for r in range(9)}
    for b in battles:
        dep = ''.join(b['deploy'])
        pops = [row_populated(b['unit_table'][r]) for r in range(9)]
        for r in range(9):
            tier_pop[r].append(pops[r])
            if pops[r] == 0:
                continue
            for t in TOKEN_LABEL:
                if t in dep:
                    tier_token[r][t] += 1

    # differential: token rate when tier populated vs all battles
    n = len(battles)
    token_given_tier = {}
    for r in range(9):
        pop_n = sum(1 for p in tier_pop[r] if p > 0)
        token_given_tier[str(r)] = {
            'battles_populated': pop_n,
            'mean_nibble_cells': round(st.mean(tier_pop[r]), 2) if tier_pop[r] else 0,
            'tokens': {
                t: {
                    'label': TOKEN_LABEL[t],
                    'count_when_populated': tier_token[r][t],
                    'rate_when_populated': round(tier_token[r][t] / pop_n, 3) if pop_n else 0,
                    'global_rate': round(sum(1 for b in battles if t in ''.join(b['deploy'])) / n, 3),
                }
                for t in sorted(TOKEN_LABEL)
            },
        }

    # wing-band -> tier hypothesis (theory from EXE row 0,1=left / 7,8=right)
    tier_wing = {
        'left_band': [0, 1, 2],
        'center_band': [3, 4, 5],
        'right_band': [6, 7, 8],
    }
    wing_scores = {}
    for wing, tiers in tier_wing.items():
        chars = WINGS[wing.replace('_band', '')]
        for r in tiers:
            pop_n = sum(1 for b in battles if row_populated(b['unit_table'][r]) > 0)
            wing_hits = sum(
                1 for b in battles
                if row_populated(b['unit_table'][r]) > 0
                and any(c in ''.join(b['deploy']) for c in chars)
            )
            wing_scores['tier_%d' % r] = {
                'wing': wing,
                'populated': pop_n,
                'has_wing_token': wing_hits,
                'wing_token_rate': round(wing_hits / pop_n, 3) if pop_n else 0,
            }

    # proposed mapping: tier row -> primary deploy tokens (rate lift vs global)
    proposed = {}
    for r in range(9):
        lifts = []
        pop_n = token_given_tier[str(r)]['battles_populated']
        for t, info in token_given_tier[str(r)]['tokens'].items():
            lift = info['rate_when_populated'] - info['global_rate']
            if pop_n >= 20 and lift > 0.02:
                lifts.append((lift, t, info['label']))
        lifts.sort(reverse=True)
        proposed['tier_%d' % r] = {
            'primary_tokens': [x[1] for x in lifts[:4]],
            'labels': [x[2] for x in lifts[:4]],
            'note': wing_scores.get('tier_%d' % r, {}),
        }

    out = {
        'source': 'hjmapdat_battles.json (38 battles)',
        'deploy_grid': '40x19 ASCII section C',
        'sect_a_rows': 9,
        'global_deploy_char_freq': dict(deploy_chars.most_common(24)),
        'token_given_tier': token_given_tier,
        'wing_correlation': wing_scores,
        'proposed_tier_tokens': proposed,
        'mapping_status': 'heuristic_wing_band; not 1:1 char->tier (tokens co-occur on full map)',
        'exe_row_semantics': {
            '0': 'left_wing_template_primary',
            '1': 'left_wing_template_main',
            '2': 'left_secondary',
            '3': 'center_reserve',
            '4': 'center_reserve_sparse',
            '5': 'center_reserve_sparse',
            '6': 'right_secondary',
            '7': 'right_wing_template_main',
            '8': 'right_wing_template_primary',
        },
    }
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    print('=== SECT_A tier population (38 battles) ===')
    for r in range(9):
        pop_n = token_given_tier[str(r)]['battles_populated']
        print(' tier_%d: populated %2d/38  mean_cells=%.1f  wing=%s rate=%.2f' % (
            r, pop_n, token_given_tier[str(r)]['mean_nibble_cells'],
            wing_scores['tier_%d' % r]['wing'],
            wing_scores['tier_%d' % r]['wing_token_rate'],
        ))

    print('\n=== Proposed token hints (lift>0.02) ===')
    for r in range(9):
        p = proposed['tier_%d' % r]
        print(' tier_%d: %s' % (r, p['primary_tokens'] or '(none)'))

    print('\nwritten', OUT)


if __name__ == '__main__':
    main()
