# -*- coding: utf-8 -*-
"""gen_dormants.py — 从 tree_data 生成休眠人物清单 -> _dormants.json
规则:
  * 树节点全集(去重) - 370 现成人物 = 休眠名单, 依序占槽 371..
  * 4 字以上独名字拆 姓/名 (拼接显示不变); 拆后仍须 GBK<=6B
  * (姓,名) 双字段的 GBK 字节预截断(6B 上限, 不得切断半字符)
输出: [{slot, sur, giv, sur_hex, giv_hex, state, rel, tree_names:[原独名]}]
"""
import json, sys
sys.path.insert(0, '.')
import tree_data as T

ents = json.load(open('ents_dump.json', encoding='utf-8'))
live = set()
for e in ents:
    live.add((e['surname'].strip(), e['given'].strip()))

persons = []  # 保序去重
seen = set()
for t in T.TREES:
    for nd in t[3]:
        key = (nd[1], nd[2])
        if key not in seen:
            seen.add(key)
            persons.append({'sur': nd[1], 'giv': nd[2], 'rel': nd[3], 'state': nd[4]})

# 独名(姓为空) 4 字+ 拆分
SPLIT = {
    '土田御前': ('土田', '御前'),
    '木下弥次郎': ('木下', '弥次郎'),
    '于大之方': ('于大', '之方'),
    '大井之方': ('大井', '之方'),
}

def gbk6(s):
    b = s.encode('gbk')
    while len(b) > 6:
        b = b[:-2] if len(b) % 2 == 0 else b[:-1]
    # 防止截半个汉字: GBK 双字节, 逐步退
    while len(b) > 6:
        b = b[:-2]
    return b

out = []
slot = 371
for p in persons:
    sur, giv = p['sur'].strip(), p['giv'].strip()
    orig = sur + giv
    if (sur, giv) in live:
        continue
    if sur == '' and giv in SPLIT:
        sur, giv = SPLIT[giv]
    sb, gb = gbk6(sur), gbk6(giv)
    assert len(sb) <= 6 and len(gb) <= 6
    assert 371 <= slot <= 511, '超出扩展槽容量'
    out.append({'slot': slot, 'sur': sur, 'giv': giv,
                'sur_hex': sb.hex(), 'giv_hex': gb.hex(),
                'state': p['state'], 'rel': p['rel'], 'orig': orig})
    slot += 1

json.dump(out, open('_dormants.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('休眠人物 %d, 槽 %d..%d' % (len(out), out[0]['slot'], out[-1]['slot']))
for o in out[:8]:
    print('  ', o['slot'], o['sur'], o['giv'], o['rel'])
