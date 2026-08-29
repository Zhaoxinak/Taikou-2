#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SECT_A (col,row) ↔ HJMAPDAT deploy 40×19 空间映射（续26）。

来源：谣言写块 0x438c60
  off = (col << 1) + 40 * ((col & 1) ^ 1) + 80 * row
  x = off % 40,  y = off // 40

偶数列 → 奇数 y 行；奇数列 → 偶数 y 行（隔行交织）。
"""
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

OUT = 'scripts/sectA_deploy_map.json'


def dep_off(col, row):
    return (col << 1) + 40 * ((col & 1) ^ 1) + 80 * row


def main():
    battles = json.load(open('hjmapdat_battles.json', encoding='utf-8'))
    # validate: populated SECT_A cells land on non-space deploy chars more than chance
    token_hits = 0
    space_hits = 0
    total = 0
    per_battle = []
    for b in battles:
        dep = ''.join(b['deploy'])
        th = sh = n = 0
        for row in range(9):
            raw = b['unit_table'][row]['raw']
            for col in range(20):
                if (raw[col] & 0xf) == 0:
                    continue
                off = dep_off(col, row)
                if off >= len(dep):
                    continue
                ch = dep[off]
                n += 1
                if ch in ' \x00':
                    sh += 1
                else:
                    th += 1
        total += n
        token_hits += th
        space_hits += sh
        per_battle.append({'id': b['id'], 'populated': n, 'nonspace': th})

    grid = []
    for row in range(9):
        row_cells = []
        for col in range(20):
            off = dep_off(col, row)
            row_cells.append({
                'col': col, 'row': row, 'deploy_off': off,
                'x': off % 40, 'y': off // 40,
            })
        grid.append(row_cells)

    out = {
        'formula': 'off = (col<<1) + 40*((col&1)^1) + 80*row',
        'source': '0x438c60 rumor/deploy edit (GAME_DATA_SPEC)',
        'deploy_grid': '40x19',
        'sect_a': '20 cols x 9 rows',
        'interleave': 'even col -> odd y; odd col -> even y',
        'validation_38_battles': {
            'populated_cells': total,
            'land_on_nonspace': token_hits,
            'land_on_space': space_hits,
            'nonspace_rate': round(token_hits / total, 3) if total else 0,
        },
        'grid': grid,
    }
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('formula: off=(col<<1)+40*((col&1)^1)+80*row')
    print('38 battles: populated=%d nonspace=%d (%.1f%%) space=%d' % (
        total, token_hits, 100.0 * token_hits / total if total else 0, space_hits))
    print('written', OUT)


if __name__ == '__main__':
    main()
