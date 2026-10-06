# -*- coding: utf-8 -*-
"""probe_s1_slots.py — 剧本实体池(SNDATA S1 = 370×59)的「登场可用槽」普查 [只读]

依据(全部静态反汇编坐实, 见 probe_appear.py 头部):
  * LoadBSDATA @0x47fa90: push 0xa154(=41300=59×700) 整块明文读 BSDATA1/2.TR2 -> 常驻 0x524a20
    ⇒ BSDATA*.TR2 文件 == 运行时武将主表, 逐字节等同(改文件=改运行时)。
  * 登场例程 0x4A4D10 (调用点 0x4A4CC0, 日期推进链):
      半A: 遍历实体槽 di=0..358 (stride 0x2f, 基址 0x519868):
           n = getter 0x49a610 = word[ent+0x2c] 低4位, 若 n>=0xc -> 视为 0xff 跳过; n<=0 跳过
           call 0x49a6b0(ent, n-1)                      -> 低4位倒数递减
           if (word[+0x2c] & 0x8000) && !(word[+0x2c] & 0x80):  收进可用槽表[esp+0x690]
      半B: 遍历 oid 0..699, 登场标志[oid]==0 且 登场年<=当前年 -> 收进候选表
      配对: min(候选,可用槽) 次 { call 0x47f7b0(slot, oid) 用 BSDATA[oid] 实例化并把姓/名写入
             slot 索引的运行时名表; 登场标志[oid]=1; call 0x4a4fc0(ent) 元服初始化 }
  * S1 段: 流内 21830B = 59×370 -> 实体池初值, 其 +0x38(word) 即实体状态字(entity+0x2c)

本脚本要回答: 1560 开局到底有几个「登场可用槽」(=0x8000置位 & 0x0080清 & 低4位∈1..0xb)。
"""
import struct, sys, os
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')

BASE = r'F:\Games\Taikou 2\Taikou2 Original'
R, N = 59, 370


def s7(r, off):
    return r[off:off + 7].split(b'\x00')[0].decode('gbk', 'replace')


def bs_names():
    d = open(os.path.join(BASE, 'BSDATA1.TR2'), 'rb').read()
    return [(s7(d[i * R:], 0) + s7(d[i * R:], 7)) for i in range(700)]


def find_s1(d, names):
    """在 SNDATA 里找 370×59 且首条有名、姓/名命中率高的区段"""
    best = []
    for off in range(0, len(d) - R * N, 2):
        hit = 0
        for i in range(0, 40):
            r = d[off + i * R: off + (i + 1) * R]
            nm = s7(r, 0) + s7(r, 7)
            if len(nm) >= 2 and nm in names:
                hit += 1
        if hit >= 30:
            best.append((off, hit))
    return best


def main():
    names = bs_names()
    for fn in ('SNDATA1.TR2', 'SNDATA2.TR2'):
        d = open(os.path.join(BASE, fn), 'rb').read()
        cands = find_s1(d, names)
        print('\n===== %s =====  S1 候选偏移: %s' % (fn, cands[:6]))
        if not cands:
            print('   !! 未定位 S1, 跳过')
            continue
        off = cands[0][0]
        recs = [d[off + i * R: off + (i + 1) * R] for i in range(N)]
        stat = [struct.unpack_from('<H', r, 0x38)[0] for r in recs]
        print('   S1@0x%X  前3条: %s' % (off, [s7(r, 0) + s7(r, 7) for r in recs[:3]]))
        print('   状态字 distinct=%d  top=%s' % (len(set(stat)), Counter(stat).most_common(8)))
        elig, empty = [], []
        for i, (r, w) in enumerate(zip(recs, stat)):
            nib = w & 0xf
            alive_out = (w & 0x8000) and not (w & 0x80)
            nm = s7(r, 0) + s7(r, 7)
            if nib >= 0xc or nib <= 0:
                pass
            elif alive_out:
                elig.append((i, nm, hex(w), nib))
            if nm == '' or (w & 0x8080) == 0x8080:
                empty.append(i)
        print('   ★登场可用槽(0x8000置/0x80清/低4位1..b) 共 %d 个:' % len(elig))
        for e in elig[:24]:
            print('      slot%-4d %-8s status=%s nib=%d' % e)
        print('   空槽/除籍(名空 或 0x8080) 共 %d 个: %s' % (len(empty), empty[:40]))
        # 低4位分布 & 位组合分布
        print('   低4位分布: %s' % Counter(w & 0xf for w in stat).most_common())
        print('   (bit15,bit7) 组合: %s' % Counter(((w >> 15) & 1, (w >> 7) & 1) for w in stat).most_common())


if __name__ == '__main__':
    main()
