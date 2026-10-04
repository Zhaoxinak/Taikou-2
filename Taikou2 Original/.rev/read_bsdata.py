# -*- coding: utf-8 -*-
"""
read_bsdata.py — 直接用工程根已破的 BSDATA 59B schema 读明文主表。
权威: docs/specs/GAME_DATA_SPEC.md §1.2 (scripts/bsdata_format_ref.py 73/73 PASS)

偏移表(59B):
  0x00..0x06 姓(GBK 7B)   0x07..0x0d 名(GBK 7B)
  0x10       bushou_id u16 (恒==记录号)
  0x14       compat u16
  0x16..0x1a 五维
  0x27       birth_year - 1490
  0x29..0x2a father_id u16 LE  (0xFFFF=无)
  0x2b       home_idx
  0x2c/0x2d/0x2e 体力上限/现役/消耗
  0x2f       ambition
  0x30       province
  0x31       city
  0x32..0x33 merit
  0x34       salary
  0x35       loyalty
  0x36..0x37 lord u16
  0x38..0x39 status_word (職位 = byte[0x39]&7)
  0x3a       archetype (>>4)
"""
import struct, sys, io, os

sys.stdout.reconfigure(encoding='utf-8')

BASE = r'F:\Games\Taikou 2\Taikou2 Original'
RSIZE = 59
NREC = 700


def load(fn):
    p = os.path.join(BASE, fn)
    d = open(p, 'rb').read()
    assert len(d) == RSIZE * NREC, '%s size=%d expect %d' % (fn, len(d), RSIZE * NREC)
    return d


def s7(raw, off):
    s = raw[off:off + 7].split(b'\x00')[0]
    try:
        return s.decode('gbk')
    except Exception:
        return '?' + s.hex()


def parse(d):
    out = []
    for i in range(NREC):
        r = d[i * RSIZE:(i + 1) * RSIZE]
        *forces, = r[0x16:0x1b]
        out.append(dict(
            idx=i,
            surname=s7(r, 0x00), given=s7(r, 0x07),
            bushou_id=struct.unpack_from('<H', r, 0x10)[0],
            forces=forces,
            birth=r[0x27] + 1490,
            father=struct.unpack_from('<H', r, 0x29)[0],
            home=r[0x2b],
            stam_max=r[0x2c], stam=r[0x2d], stam_drain=r[0x2e],
            ambition=r[0x2f],
            province=r[0x30], city=r[0x31],
            merit=struct.unpack_from('<H', r, 0x32)[0],
            salary=r[0x34], loyalty=r[0x35],
            lord=struct.unpack_from('<H', r, 0x36)[0],
            status=struct.unpack_from('<H', r, 0x38)[0],
            rank=struct.unpack_from('<H', r, 0x38)[0] >> 8 & 7,
            archetype=r[0x3a] >> 4,
            raw=r,
        ))
    return out


def name(o):
    return o['surname'] + o['given']


def main():
    for fn in ('BSDATA1.TR2', 'BSDATA2.TR2'):
        d = load(fn)
        recs = parse(d)
        print('=========== %s ===========' % fn)
        print('前 12 条:', [name(o) for o in recs[:12]])
        nf = [o for o in recs if o['father'] != 0xFFFF]
        bad = [o for o in nf if o['father'] >= NREC]
        print('有父亲记录: %d / %d   越界 father_id: %d' % (len(nf), NREC, len(bad)))
        # 自洽性: father 指向的必须是真实人物(非占位槽)
        placeholders = {i for i, o in enumerate(recs) if o['surname'].startswith('姓0')}
        print('占位槽:', sorted(placeholders))
        # 抽查: 父子姓名对
        print('--- 前 20 组父子关系 ---')
        seen = 0
        for o in recs:
            if o['father'] == 0xFFFF or o['father'] >= NREC:
                continue
            f = recs[o['father']]
            print('   %-10s(id%3d, 生%d) ← 父 %-10s(id%3d, 生%d)' %
                  (name(o), o['idx'], o['birth'], name(f), f['idx'], f['birth']))
            seen += 1
            if seen >= 20:
                break
        seen[fn[:7]] = recs
        print()
    return seen['BSDATA1'], seen['BSDATA2']


if __name__ == '__main__':
    a, b = main()
    print()
    print('=========== 柴田胜家(id=1) 家族树 ===========')
    recs = a
    kids = {}
    for o in recs:
        if o['father'] != 0xFFFF and o['father'] < NREC:
            kids.setdefault(o['father'], []).append(o['idx'])

    def tree(root, depth=0, out=None, seen=None):
        if out is None:
            out, seen = [], set()
        if root in seen or depth > 6:
            return out
        seen.add(root)
        out.append((depth, root))
        for c in kids.get(root, []):
            tree(c, depth + 1, out, seen)
        return out

    for _d, i in tree(1):
        o = recs[i]
        print('   %s%-12s id=%-4d 生=%d 父=%-4d 城=%s 主=%s 職位=%d arche=%d' %
              ('  ' * _d, name(o), o['idx'], o['birth'], o['father'],
               o['city'], o['lord'], o['rank'], o['archetype']))
