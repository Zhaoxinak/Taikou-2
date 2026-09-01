#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SNDATA S14 = 49 国外交关系矩阵（严格上三角，49×48/2 = 1176B）

索引（续95 反汇编 `0x49fd80` rel_lookup 得出）：
    i = (provA - 0x5179b8) / 14 ; j = (provB - 0x5179b8) / 14
    i > j 时交换（上三角归一化）；i == j 返回 NULL（无对角）
    ecx = 48*i - i*(i-1)/2
    addr = 0x51dc5f + (j + ecx - i)  ≡  0x51dc60 + tri(i,j)
    tri(i,j) = j - i - 1 + 48*i - i*(i-1)//2        (i < j)

每「国对」1 字节，两位域：
    bit0-2 = 外交関係（8 级，0..7）
    bit3-4 = 主从関係（4 级，0..3）
🔑 编译器把 +1 折进索引算术，故代码里出现的是 **0x51dc5f**（基址 −1）——
   续100 首轮只扫 0x51dc60 因而误判「无消费方」，于此更正。
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
N_PROV = 49
MAT_BYTES = N_PROV * (N_PROV - 1) // 2      # 1176
# S14 在流中的偏移 = 前 14 段长度之和
S14_OFF = sum([22, 21830, 5200, 245, 539, 180, 46, 3200, 360, 80,
               120, 3800, 160, 2280])


def u16(b, i):
    return b[i] | (b[i + 1] << 8)


def decode(fn):
    data = open(os.path.join(ROOT, fn), 'rb').read()
    key = data[0x12] ^ data[0x13]
    return bytes(x ^ key for x in data[STREAM_BASE:])


def tri(i, j):
    """严格上三角索引，要求 i < j"""
    if i > j:
        i, j = j, i
    assert i < j, '对角线无存储（i==j 返回 NULL）'
    return j - i - 1 + 48 * i - i * (i - 1) // 2


def parse(blob):
    m = {}
    for i in range(N_PROV):
        for j in range(i + 1, N_PROV):
            v = blob[tri(i, j)]
            m[(i, j)] = {'raw': v, 'diplo': v & 7, 'master': (v >> 3) & 3}
    return m


def main():
    ok = fail = 0
    def chk(label, cond):
        nonlocal ok, fail
        if cond: ok += 1; print(f'  [PASS] {label}')
        else:    fail += 1; print(f'  [FAIL] {label}')

    names = json.load(open(os.path.join(ROOT, _ROOT + '/scripts/province_politics.json'),
                           encoding='utf-8'))['province_names']
    print('=== 49 国外交关系矩阵（S14，上三角） ===')
    chk(f'矩阵字节数 = 49*48/2 = {MAT_BYTES}', MAT_BYTES == 1176)
    chk('索引上界 tri(47,48) = 1175', tri(47, 48) == 1175)
    chk('tri(0,1)=0 / tri(0,48)=47 / tri(1,2)=48',
        tri(0, 1) == 0 and tri(0, 48) == 47 and tri(1, 2) == 48)
    idxs = sorted(tri(i, j) for i in range(N_PROV) for j in range(i + 1, N_PROV))
    chk('索引为 0..1175 的无重排列', idxs == list(range(MAT_BYTES)))

    out = {'shape': '49x49 strict-upper-triangular (no diagonal)',
           'bytes': MAT_BYTES, 'base_va': '0x51dc60',
           'accessor': '0x49fd80 (uses 0x51dc5f = base-1)',
           'bitfields': {'bit0-2': 'diplomacy 0..7', 'bit3-4': 'master-vassal 0..3'},
           'index': 'tri(i,j) = j-i-1 + 48*i - i*(i-1)//2  (i<j)'}
    for sc, fn in (('scenario1', _ROOT + '/Taikou2 Original/SNDATA1.TR2'),
                   ('scenario2', _ROOT + '/Taikou2 Original/SNDATA2.TR2')):
        s = decode(fn)
        blob = s[S14_OFF:S14_OFF + MAT_BYTES]
        m = parse(blob)
        print(f'\n--- {sc} ---')
        dv = [p['diplo'] for p in m.values()]
        mv = [p['master'] for p in m.values()]
        chk('外交関係 全部 0..7（8 级）', all(0 <= v <= 7 for v in dv))
        chk('主从関係 全部 0..3（4 级）', all(0 <= v <= 3 for v in mv))
        chk('原始字节 = diplo | master<<3',
            all(p['raw'] == (p['master'] << 3) | p['diplo'] for p in m.values()))
        nd = sum(1 for p in m.values() if p['diplo'] != 3 or p['master'] != 0)
        print(f'  非默认(外交≠3 或 主从≠0) 的国对: {nd} / {len(m)}')
        pairs = []
        for (i, j), p in sorted(m.items()):
            if p['diplo'] != 3 or p['master'] != 0:
                pairs.append({'a': names[i], 'b': names[j], 'ai': i, 'bj': j,
                              'diplo': p['diplo'], 'master': p['master'],
                              'raw': p['raw']})
        for p in pairs[:12]:
            print(f"    {p['a']}({p['ai']:2d}) - {p['b']}({p['bj']:2d}): "
                  f"外交={p['diplo']} 主从={p['master']} raw={p['raw']}")
        if len(pairs) > 12:
            print(f'    ... 另 {len(pairs) - 12} 对')
        out[sc] = {'non_default_pairs': pairs,
                   'diplo_dist': {str(k): dv.count(k) for k in range(8)},
                   'master_dist': {str(k): mv.count(k) for k in range(4)}}

    with open(os.path.join(ROOT, _ROOT + '/scripts/diplomacy_matrix.json'), 'w',
              encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f'\n==== {ok} PASS / {fail} FAIL ====')
    print('saved scripts/diplomacy_matrix.json')
    return 0 if fail == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
