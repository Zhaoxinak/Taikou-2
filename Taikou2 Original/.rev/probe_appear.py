# -*- coding: utf-8 -*-
"""probe_appear.py — 动态登场(元服)机制数据侧核查 [只读, 不改任何文件]

静态依据 (TAIK2W95_zoom.exe, 反汇编 0x4A4D10 = 登场例程, 调用点 0x4A4CC0):
    push 0x27 ; mov ecx, 0x524a20 ; call 0x4eb5c0     -> eax = BSDATA 记录0 的字段 0x27 指针
    mov ebx, 0x519288                                  -> 登场标志表基址
    循环 si = oid 0..699:
        cmp byte[ebx], 0 ; jne skip                    -> 标志!=0(已登场) 直接跳过
        cx = word[eax]        (LE, = BSDATA rec[oid] 的 0x27..0x28 两字节)
        dx = (cx >> 7) & 0x3f                          -> 6bit 「登场年偏移」
        cmp dx, word[esp+0x14] ; ja skip               -> 登场年 > 当前年 则不登场
            候选[di] = (oid, cx)                        (word[esp+0x14] = byte[0x5205f0] = 年-1560)
        add eax, 0x3b ; inc ebx ; inc si ; cmp si,0x2bc -> 记录长 59, oid 上界 700
    候选数 > 空槽数 时按 cx 排序取前 bp; 配对空槽后:
        call 0x47f7b0(&blk, slot, oid)                 -> 用 BSDATA[oid] 实例化到实体槽
        mov byte[oid+0x519288], 1                      -> 置登场标志
        call 0x4a4fc0(entity)                          -> 激活

=> BSDATA +0x27 是**打包位域**: bit0..6 = 生年偏移, bit7..12 = 登场年偏移(1560+0..63)。
   之前发现的 "birth byte 0x80 标志位" 其实就是登场年偏移的最低位, 不是死亡位。

本脚本验证三件事:
  A) 打包解出的 生年/登场年 是否史实自洽(登场年≈生年+元服年龄)
  B) 剧本 登场标志 与 登场年 的对应关系(标志=0 的人登场年是否都 > 1560)
  C) 族谱人物(尤其森长可/森兰丸)的真实登场条件与所属城/国/势力
"""
import struct, sys, os, json
sys.stdout.reconfigure(encoding='utf-8')

BASE = r'F:\Games\Taikou 2\Taikou2 Original'
RSIZE, NREC = 59, 700


def s7(r, off):
    return r[off:off + 7].split(b'\x00')[0].decode('gbk', 'replace')


def load_bs(fn):
    d = open(os.path.join(BASE, fn), 'rb').read()
    assert len(d) == RSIZE * NREC, (fn, len(d))
    out = []
    for i in range(NREC):
        r = d[i * RSIZE:(i + 1) * RSIZE]
        w = struct.unpack_from('<H', r, 0x27)[0]
        out.append(dict(
            idx=i, name=s7(r, 0) + s7(r, 7),
            birth_raw=r[0x27], next_raw=r[0x28],
            birth=1490 + (w & 0x7f),
            appear=1560 + ((w >> 7) & 0x3f),
            hi3=(w >> 13) & 7,
            father=struct.unpack_from('<H', r, 0x29)[0],
            home=r[0x2b], province=r[0x30], city=r[0x31],
            lord=struct.unpack_from('<H', r, 0x36)[0],
            status=struct.unpack_from('<H', r, 0x38)[0],
            rank=r[0x39] & 7,
        ))
    return out


def flags_from_sn(fn):
    """SNDATA 场景块: 明文? 头 'TAIKOU2_SCENARIO' @0, 700B 登场标志 @0x14"""
    d = open(os.path.join(BASE, fn), 'rb').read()
    print('  %s size=%d head=%r' % (fn, len(d), d[:20]))
    return d[0x14:0x14 + NREC]


def main():
    bs1, bs2 = load_bs('BSDATA1.TR2'), load_bs('BSDATA2.TR2')
    for tag, bs in (('BSDATA1', bs1), ('BSDATA2', bs2)):
        print('\n===== %s 打包位域分布 =====' % tag)
        ap = [o['appear'] for o in bs]
        bi = [o['birth'] for o in bs]
        print('  生年: min=%d max=%d | 登场年: min=%d max=%d' % (min(bi), max(bi), min(ap), max(ap)))
        from collections import Counter
        print('  登场年 top: %s' % Counter(ap).most_common(12))
        age = [o['appear'] - o['birth'] for o in bs]
        print('  登场年龄(登场年-生年) 分布: %s' % Counter(age).most_common(14))
        # 高 3 bit 值域
        print('  高3bit(w>>13) 分布: %s' % Counter(o['hi3'] for o in bs).most_common())

    sn = {}
    for fn in ('SNDATA1.TR2', 'SNDATA2.TR2'):
        f = flags_from_sn(fn)
        sn[fn] = f
        print('    %s 标志: ones=%d zeros=%d distinct=%s' % (fn, sum(1 for x in f if x),
                                                             sum(1 for x in f if not x), sorted(set(f))))

    # 交叉: 标志=1 vs 标志=0 的登场年
    for fn, f in sn.items():
        print('\n===== %s 登场标志 x BSDATA1 登场年 =====' % fn)
        on = [bs1[i]['appear'] for i in range(NREC) if f[i]]
        off = [bs1[i]['appear'] for i in range(NREC) if not f[i]]
        print('  标志=1(%d): 登场年 min=%s max=%s' % (len(on), min(on) if on else '-', max(on) if on else '-'))
        print('  标志=0(%d): 登场年分布 %s' % (len(off), sorted(set(off))))

    # 族谱人物核查
    print('\n===== 重点人物 =====')
    focus = ['森可成', '森长可', '森兰丸', '森定久', '森忠政', '织田信长', '织田信忠',
             '前田庆次', '森松寿丸', '真田幸村', '木下藤吉郎', '明智秀满', '武田胜赖',
             '德川信康', '今川氏真', '上杉景胜', '伊达政宗', '佐助']
    for o in bs1:
        if o['name'] in focus:
            fl = [sn[k][o['idx']] for k in sn]
            print('  %-6s id=%-4d 生%-4d 登场%-4d hi3=%d 父=%-5s home=%-3d 国=%-3d 城=%-3d lord=%-5d 職位=%d | 标志%s'
                  % (o['name'], o['idx'], o['birth'], o['appear'], o['hi3'], o['father'],
                     o['home'], o['province'], o['city'], o['lord'], o['rank'], fl))

    # 全体 标志=0 且 登场年<=1560 的人(理论上应立即登场)
    for fn, f in sn.items():
        bad = [o for o in bs1 if not f[o['idx']] and o['appear'] <= 1560]
        print('\n  %s: 标志=0 且 登场年<=1560 共 %d 人 (未被例程实例化 => 永久缺席?)' % (fn, len(bad)))
        for o in bad[:20]:
            print('     %-8s id=%-4d 生%d 登场%d 城=%d 国=%d' % (o['name'], o['idx'], o['birth'], o['appear'], o['city'], o['province']))


if __name__ == '__main__':
    main()
