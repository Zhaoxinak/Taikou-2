# -*- coding: utf-8 -*-
"""
analyze_shibata.py — 柴田胜家家族图谱分析 (BSDATA + SNDATA 登场标志)

权威来源(工程根已破, 非本机猜测):
  docs/specs/GAME_DATA_SPEC.md §1.2   BSDATA 59B schema (scripts/bsdata_format_ref.py 73/73)
  docs/specs/SNDATA_SPEC.md §...      700B 武将登场标志 @SNDATA 0x14 (= SAVEDATA 0x1ac) -> 0x519288

BSDATA 59B 关键偏移:
  0x00..0x06 姓   0x07..0x0d 名   0x10 bushou_id u16
  0x16..0x1a 五维  0x1b..0x1d 技能包
  0x27 birth-1490  0x29..0x2a father_id u16 (FFFF=无)
  0x30 province  0x31 city  0x32..0x33 merit  0x35 loyalty
  0x36..0x37 lord u16   0x38..0x39 status(職位=byte[0x39]&7)  0x3a archetype
"""
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
        return '<?>%s' % s.hex()


def load_bsdata(fn):
    p = os.path.join(BASE, fn)
    d = open(p, 'rb').read()
    assert len(d) == RSIZE * NREC, (fn, len(d))
    out = []
    for i in range(NREC):
        r = d[i * RSIZE:(i + 1) * RSIZE]
        out.append(dict(
            idx=i, surname=s7(r, 0x00), given=s7(r, 0x07),
            bushou_id=struct.unpack_from('<H', r, 0x10)[0],
            forces=list(r[0x16:0x1b]),
            birth=r[0x27] + 1490,
            father=struct.unpack_from('<H', r, 0x29)[0],
            province=r[0x30], city=r[0x31],
            merit=struct.unpack_from('<H', r, 0x32)[0],
            salary=r[0x34], loyalty=r[0x35],
            lord=struct.unpack_from('<H', r, 0x36)[0],
            status=struct.unpack_from('<H', r, 0x38)[0],
            rank=r[0x39] & 7,
            archetype=r[0x3a] >> 4,
        ))
    return out


def load_appear(fn):
    """700B 武将登场标志 @SNDATA 0x14"""
    p = os.path.join(BASE, fn)
    d = open(p, 'rb').read()
    head = d[:16]
    flag = d[0x14:0x14 + NREC]
    return head, flag


def nm(o):
    return o['surname'] + o['given']


def main():
    b1 = load_bsdata('BSDATA1.TR2')
    h1, f1 = load_appear('SNDATA1.TR2')
    print('SNDATA1 magic = %r' % h1)

    by_kw = [o for o in b1 if o['surname'] in ('柴田', '佐久间')]
    print()
    print('===== BSDATA1 中 姓=柴田/佐久间 的全部武将 =====')
    print('%-4s %-10s %-6s %-6s %-6s %-5s %-5s %-5s %s' %
          ('id', '姓名', '父', '父名', '生年', '城', '主君', '職位', '登场标志'))
    for o in by_kw:
        fa = b1[o['father']] if 0 <= o['father'] < NREC else None
        print('%-4d %-10s %-6s %-6s %-6d %-5s %-5s %-5s %s' %
              (o['idx'], nm(o),
               o['father'] if o['father'] != 0xFFFF else '无',
               nm(fa) if fa else '—',
               o['birth'],
               o['city'] if o['city'] != 255 else '浪人',
               o['lord'] if o['lord'] != 0xFFFF else '浪人',
               RANK[o['rank']],
               hex(f1[o['idx']]) if o['idx'] < len(f1) else '?'))

    # ---- 登场标志值域 ----
    from collections import Counter
    print()
    print('登场标志值域:', Counter(f1).most_common(6))
    print('非0 数量: %d / 700' % sum(1 for v in f1 if v))

    # ---- 柴田家树(id=1) ----
    kids = {}
    for o in b1:
        if 0 <= o['father'] < NREC:
            kids.setdefault(o['father'], []).append(o['idx'])
    print()
    print('===== 按 father_id 链: 柴田胜家(id=1) 血统树 =====')

    def walk(root, d=0, seen=None, out=None):
        if out is None:
            out, seen = [], set()
        if root in seen or d > 5:
            return out
        seen.add(root)
        out.append((d, root))
        for c in kids.get(root, []):
            walk(c, d + 1, seen, out)
        return out

    for d, i in walk(1):
        o = b1[i]
        print('   %s%-10s id=%-4d 生%d 城%s 主%s 職位%s 登场%s' %
              ('   ' * d, nm(o), o['idx'], o['birth'],
               o['city'] if o['city'] != 255 else '浪人',
               o['lord'] if o['lord'] != 0xFFFF else '浪人',
               RANK[o['rank']], f1[o['idx']]))
    return b1, f1


if __name__ == '__main__':
    main()
