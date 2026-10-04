# -*- coding: utf-8 -*-
import struct, sys, os
sys.stdout.reconfigure(encoding='utf-8')
BASE = r'F:\Games\Taikou 2\Taikou2 Original'
RSIZE, NREC = 59, 700
RANK = ['无', '足轻组头', '足轻工头', '足轻头', '家老', '组头', '家臣', '大名']

def s7(raw, off):
    s = raw[off:off + 7].split(b'\x00')[0]
    try:
        return s.decode('gbk')
    except Exception:
        return '<?>'

def load(fn):
    d = open(os.path.join(BASE, fn), 'rb').read()
    assert len(d) == RSIZE * NREC
    return d

def parse(r, i):
    return dict(idx=i, sur=s7(r, 0), giv=s7(r, 7),
               bushou=struct.unpack_from('<H', r, 0x10)[0],
               forces=list(r[0x16:0x1b]), birth=r[0x27] + 1490,
               father=struct.unpack_from('<H', r, 0x29)[0],
               prov=r[0x30], city=r[0x31],
               merit=struct.unpack_from('<H', r, 0x32)[0],
               salary=r[0x34], loyalty=r[0x35],
               lord=struct.unpack_from('<H', r, 0x36)[0],
               status=struct.unpack_from('<H', r, 0x38)[0],
               rank=r[0x39] & 7, archetype=r[0x3a] >> 4)

d = load('BSDATA1.TR2')
recs = [parse(d[i*RSIZE:(i+1)*RSIZE], i) for i in range(NREC)]

def find(sur=None, giv=None):
    out = []
    for o in recs:
        if sur and o['sur'] != sur: continue
        if giv and giv not in o['giv']: continue
        out.append(o)
    return out

print('===== 织田信长 / 浅井长政 / 关键人物 ID =====')
for o in find(sur='织田'):
    if '信' in o['giv']:
        print('  织田 %s id=%d birth=%d prov=%d city=%s lord=%s rank=%s arch=%d'
              % (o['giv'], o['idx'], o['birth'], o['prov'],
                 o['city'] if o['city']!=255 else '浪人',
                 o['lord'] if o['lord']!=0xFFFF else '浪人',
                 RANK[o['rank']], o['archetype']))
for o in find(sur='浅井'):
    print('  浅井 %s id=%d birth=%d prov=%d city=%s lord=%s rank=%s arch=%d'
          % (o['giv'], o['idx'], o['birth'], o['prov'],
             o['city'] if o['city']!=255 else '浪人',
             o['lord'] if o['lord']!=0xFFFF else '浪人',
             RANK[o['rank']], o['archetype']))

print()
print('===== 现有女性武将(名含 の方 或已知女名) =====')
fem_kw = ('の方', '浓姬', '浓姫', 'ねね', '阿市', '茶茶', '初', '江', '鹤', '松', '千')
for o in recs:
    nm = o['sur'] + o['giv']
    if any(k in nm for k in fem_kw):
        print('  %-10s id=%-4d birth=%d prov=%d city=%s lord=%s rank=%s arch=%d forces=%s'
              % (nm, o['idx'], o['birth'], o['prov'],
                 o['city'] if o['city']!=255 else '浪人',
                 o['lord'] if o['lord']!=0xFFFF else '浪人',
                 RANK[o['rank']], o['archetype'], o['forces']))

print()
print('===== 现有 柴田/浅井/织田 一门(供克隆参考) =====')
for o in recs:
    if o['sur'] in ('柴田', '浅井', '织田'):
        print('  %-10s id=%-4d birth=%d prov=%d city=%s lord=%s rank=%s arch=%d merit=%d loy=%d forces=%s'
              % (o['sur']+o['giv'], o['idx'], o['birth'], o['prov'],
                 o['city'] if o['city']!=255 else '浪人',
                 o['lord'] if o['lord']!=0xFFFF else '浪人',
                 RANK[o['rank']], o['archetype'], o['merit'], o['loyalty'], o['forces']))

print()
print('===== 槽位 690..699 当前内容 =====')
for i in range(690, 700):
    o = recs[i]
    print('  %3d  %-10s bushou=%d birth=%d father=%d prov=%d city=%s lord=%s rank=%s arch=%d merit=%d loy=%d'
          % (i, (o['sur']+o['giv']) if o['sur'] else '(空)', o['bushou'],
             o['birth'], o['father'], o['prov'], o['city'], o['lord'], RANK[o['rank']], o['archetype'], o['merit'], o['loyalty']))

print()
print('===== 模板记录全 hex =====')
for tid in (1, 36):
    r = d[tid*RSIZE:(tid+1)*RSIZE]
    print('  id=%d : %s' % (tid, r.hex()))
