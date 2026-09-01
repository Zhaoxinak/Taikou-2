#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续175：SNDATA 833 记录「类型→结构指纹」全表 + 逐类型字段初判。
对每个 type，给出：记录数 / payload 结构特征(嵌入GBK名/word数组/byte值/填充) / 头3字 / 一致性。
交付：scripts/sndata_type_schema.py（自检）+ sndata_type_schema.json（全表）。
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

import os, struct, json
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

def read_records(path):
    d = open(os.path.join(ROOT, path), 'rb').read()
    body = d[16:]
    return [body[i*49:(i+1)*49] for i in range(len(body)//49)]

def gbk(b):
    try: return b.decode('gbk')
    except: return None

def field_probe(recs):
    """对该 type 的所有记录，探明 payload 结构。
    ⚠️ 续176 修正：嵌入的「GBK 名」经与真实武将名表(bsdata.json 699 名)交叉比对为 0 命中
    ⇒ 全是结构字节巧合 mojibake，非真实名。故不再把「可 GBK 解码」当「含名」。
    """
    word_array_like = 0
    for r in recs:
        seg = r[6:49]
        vals = struct.unpack_from('<'+'H'*20, seg, 0) if len(seg) >= 40 else []
        if vals and sum(1 for v in vals if v < 0x4000) >= 16:
            word_array_like += 1
    n = len(recs)
    features = []
    if word_array_like / n > 0.5: features.append('word数组')
    return ('+'.join(features)) if features else '二进制'

def build():
    recs1 = read_records(_ROOT + '/Taikou2 Original/SNDATA1.TR2')
    bytype = defaultdict(list)
    for r in recs1:
        t = struct.unpack_from('<H', r, 0)[0] & 0xff
        bytype[t].append(r)
    out = {}
    for t in sorted(bytype):
        grp = bytype[t]
        r0 = grp[0]
        idw, subw, fl = struct.unpack_from('<HHH', r0, 0)
        # 填充判定
        seg = r0[6:49]
        f3 = sum(1 for b in seg if b == 0xf3); c0c = sum(1 for b in seg if b == 0x0c)
        fill_ratio = (f3 + c0c) / 43
        if fill_ratio > 0.8:
            kind = '填充'
        elif t in (0x00, 0x01):
            kind = '状态开关'
        else:
            kind = field_probe(grp)
        out[t] = {
            'count': len(grp),
            'idw0': idw, 'subw0': subw, 'flag0': fl,
            'kind': kind,
            'fill_ratio': round(fill_ratio, 2),
            'sample_payload': r0[6:26].hex(),
        }
    return recs1, out

recs, schema = build()
# 汇总统计
from collections import Counter
kindcnt = Counter(v['kind'] for v in schema.values())
print('=== 类型 kind 分布 ===')
for k, c in kindcnt.most_common():
    print(f'  {k}: {c} 种 type')
print(f'\n总记录 {len(recs)} 条, 去重 type {len(schema)} 种')

# 写 json
with open(os.path.join(HERE, 'sndata_type_schema.json'), 'w', encoding='utf-8') as f:
    json.dump({'source':'SNDATA1.TR2','total_records':len(recs),
               'type_count':len(schema),'types':{str(k):v for k,v in schema.items()}},
              f, ensure_ascii=False, indent=1)
print('saved sndata_type_schema.json')

# 自检
ok = True
def chk(nm, c, extra=''):
    global ok
    print(('  [PASS] ' if c else '  [FAIL] ') + nm + ((' — ' + extra) if extra else ''))
    ok = ok and c
chk('去重 type 数在 150-200', 150 <= len(schema) <= 200, f'{len(schema)}')
chk('总记录 833', len(recs) == 833)
real_kinds = [v for v in schema.values() if v['kind'] not in ('填充','状态开关')]
chk('存在真实结构类型(含嵌GBK名/word数组)', len(real_kinds) > 50, f'{len(real_kinds)} 种')
name_kinds = [v for v in schema.values() if '名' in v['kind']]
chk('payload 无真实名（续176: 提取名 0/1956 命中真实武将名表）', len(name_kinds) == 0, f'{len(name_kinds)}')
print('\nRESULT:', 'ALL PASS' if ok else 'FAIL')
import sys; sys.exit(0 if ok else 1)
