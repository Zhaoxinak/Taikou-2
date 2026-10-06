# -*- coding: utf-8 -*-
"""chk_namepolarity2.py — 判定两件事
 1) 运行时姓名字表(0x520660 / 0x521AA8)到底哪张放姓: 已定(见 _namepolarity.txt), 这里再独立复核
 2) ents_dump 里 n>=5 的整位偏移: 是"运行用的是当前 BSDATA1.TR2(已被MOD改过)"还是"表按 slot 索引"
输出 -> _namepolarity2.txt
"""
import json, os, struct

ROOT = r'F:\Games\Taikou 2\Taikou2 Original'
REV = os.path.join(ROOT, '.rev')
R, NREC = 59, 700
TA, TB = 0x520660, 0x521AA8
out = open(os.path.join(REV, '_namepolarity2.txt'), 'w', encoding='utf-8')
w = lambda *a: print(*a, file=out)


def gbk7(b):
    return b.split(b'\0')[0].decode('gbk', 'replace')


def recs(p):
    d = open(p, 'rb').read()
    return [d[i * R:i * R + R] for i in range(NREC)] if len(d) == R * NREC else None, d


cur = recs(os.path.join(ROOT, 'BSDATA1.TR2'))
orig = recs(os.path.join(ROOT, 'BSDATA1.TR2.orig'))
Dcur, Dorig = cur[1], orig[1]
w('BSDATA1.TR2 %d B / .orig %d B' % (len(Dcur), len(Dorig)))
diff = [i for i in range(NREC) if cur[0][i] != orig[0][i]]
w('记录内容不同的 oid: %d 个 -> %s' % (len(diff), diff[:40]))
for i in diff[:12]:
    w('  oid %-4d cur: %-8s %-8s | orig: %-8s %-8s' %
      (i, gbk7(cur[0][i][0:7]), gbk7(cur[0][i][7:14]), gbk7(orig[0][i][0:7]), gbk7(orig[0][i][7:14])))

# ---- 把 ents_dump 的两表按「当前 BSDATA」再对一次 ----
ents = json.load(open(os.path.join(REV, 'ents_dump.json'), encoding='utf-8'))
tabA = {e['oid']: e['given'] for e in ents}      # dump_ents: given <- TA(0x520660)
tabB = {e['oid']: e['surname'] for e in ents}    #             surname <- TB(0x521AA8)
for src, rs in (('当前 BSDATA1.TR2', cur[0]), ('原始 .orig', orig[0])):
    sa = ca = sb = cb = 0
    for k, v in tabB.items():
        if not v or v == '?':
            continue
        f0, f1 = gbk7(rs[k][0:7]), gbk7(rs[k][7:14])
        if v == f0:
            sb += 1
        elif v == f1:
            cb += 1
    for k, v in tabA.items():
        if not v or v == '?':
            continue
        f0, f1 = gbk7(rs[k][0:7]), gbk7(rs[k][7:14])
        if v == f0:
            sa += 1
        elif v == f1:
            ca += 1
    w('\n对 %s: TB(0x521AA8) 命中rec[0:7] %d / rec[7:14] %d ; TA(0x520660) 命中rec[0:7] %d / rec[7:14] %d'
      % (src, sb, cb, sa, ca))

# ---- 偏移检测: tabB[i] 是否等于 rec[i+1] 的姓 ----
w('\n=== 整位偏移检测(以 .orig 为准) ===')
hit_same = hit_plus1 = 0
for i in range(0, 360):
    f0 = gbk7(orig[0][i][0:7])
    f0n = gbk7(orig[0][i + 1][0:7]) if i + 1 < NREC else ''
    v = tabB.get(i, '')
    if not v or v == '?':
        continue
    if v == f0:
        hit_same += 1
    if v and v == f0n:
        hit_plus1 += 1
w('TB[i]==orig姓[i] 命中 %d ; TB[i]==orig姓[i+1] 命中 %d' % (hit_same, hit_plus1))

# 用 SNDATA 登场标志解释偏移: 场景1 中 oid 5 是否在开场名单?
flags = open(os.path.join(ROOT, 'SNDATA1.TR2'), 'rb').read()[0x14:0x14 + NREC]
w('\nSNDATA1 开场在场标志 前 12: %s' % list(flags[:12]))
w('oid5 下方贞清 在场? %s' % bool(flags[5]))

# 反推: 若表按「开场名单顺序」而非 oid 索引, 则 tabB[slot] = 第 slot 个在场者的姓
live = [i for i in range(NREC) if flags[i]]
w('在场人数 %d ; 前 12 个在场 oid: %s' % (len(live), live[:12]))
m = sum(1 for s in range(min(370, len(live))) if tabB.get(s) == gbk7(orig[0][live[s]][0:7]))
w('假设「表按在场顺序索引」: 前 370 位命中 %d' % m)
m2 = sum(1 for s in range(370) if tabB.get(s) and tabB[s] == gbk7(orig[0][s][0:7]))
w('假设「表按 oid 索引」  : 前 370 位命中 %d' % m2)
out.close()
print('-> .rev/_namepolarity2.txt')
