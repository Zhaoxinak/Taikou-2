# -*- coding: utf-8 -*-
"""
gen_appear_patch.py —— 动态元服/登场 的数据侧补丁 (等长原位改写 BSDATA*.TR2 的「登场年」字段)

【机制(本次静态反汇编闭死, 详见 probe_appear.py / probe_s1_slots.py 头部)】
  BSDATA 记录 59B 偏移 0x27 处的 **u16 位域**:
      bits 0..6  = 生年 - 1490          (modkit 旧解析把整字节当生年 -> 之前 +128 假象的真因)
      bits 7..12 = 登场年 - 1560 (0..63) —— 引擎的「元服/登场年」
      bits 13..15= 另一 3bit 字段(本脚本原样保留)
  登场例程 `0x4A4D10`(唯一调用点 0x4A4CC0, 在日期推进链 0x4A0DED 内 => **每月过一次**):
      半A 遍历实体槽: n=getter0x49a610(word[ent+0x2c]低4位, >=0xc 视作无); n∈1..0xb 则递减并
          当 (word&0x8000)!=0 且 (word&0x80)==0 时把槽收进「可用槽表」
      半B 遍历 oid 0..699: 登场标志[oid]==0 且 (登场年-1560) <= 当前年偏移(byte 0x5205f0) => 收进候选表
      配对 min(候选,可用槽): call 0x47f7b0(槽,oid) 用 BSDATA[oid] 实例化实体 + 把姓/名写进按**槽**索引的
          运行时名表; 登场标志[oid]=1; call 0x4a4fc0 元服初始化
  => 「登场」= **空缺递补**: 需要一个「待登场槽」(bit15置位/bit7清零/低4位1..b) + 一个已到登当年的未登场 oid。
     发布数据里 0 个待登场槽(全 370 槽低4位=0xf) => 原生登场通道从未开火, 这就是 森长可/阿市 永远不见的原因。
     big.exe 的 4i 步把扩展槽改造成待登场槽并冻结倒数, 本脚本负责让「谁何时登场」可控。

【本脚本策略】
  目标集 = 族谱里能确切对上 BSDATA 档案的人(conf exact/alias) + 数据里天然挂着的 695..699
           (柴田胜政/阿市/浅井茶茶/浅井初/浅井江 —— 剧本标志=0 且 登场年=1560, 是官方留的待登场档案)
  * 目标集内且该剧本标志=0  => 登场年 = 生年 + 元服年龄(默认15), 夹到 [1561, 1623]
  * 其余标志=0 的所有人     => 登场年 = 1623 (挂到宇宙尽头 = 实际不登场)
      理由: 发布数据有 138 人登场年=1561, 通道一开就会在 1561 年一次性灌满 141 个待登场槽并挤爆地图。
  * 标志=1(剧本已登场)者一律不动。

只改 2 个字节里的 6 个位, 记录长度/偏移/旧存档格式完全不变(登场标志与实体池初值都不动)。
幂等: 首次运行把原件备份为 *.TR2.orig, 以后每次都从 .orig 重建。
"""
import json, os, struct, sys
sys.stdout.reconfigure(encoding='utf-8')

ROOT = r'F:\Games\Taikou 2\Taikou2 Original'
R, NREC, NPLAY = 59, 700, 370
GENPEUKU_AGE = 15          # 元服年龄: 登场年 = 生年 + 该值
SUSPEND = 63               # 登场年偏移 63 = 1623, 事实上不登场
EXTRA = {695: '柴田胜政', 696: '阿市', 697: '浅井茶茶', 698: '浅井初', 699: '浅井江'}
PAIRS = (('BSDATA1.TR2', 'SNDATA1.TR2'), ('BSDATA2.TR2', 'SNDATA2.TR2'))


def s7(r, off):
    return r[off:off + 7].split(b'\x00')[0].decode('gbk', 'replace')


def target_oids():
    """族谱 -> BSDATA 档案 oid, 只信 exact/alias (fuzzy 会张冠李戴)"""
    m = json.load(open(os.path.join(ROOT, '.rev', '_tree_oid_map.json'), encoding='utf-8'))
    out = {}
    for e in m:
        if e.get('conf') in ('exact', 'alias') and isinstance(e.get('oid'), int):
            nm = (e['officer'] or {}).get('name') or (e['sur'] + e['giv'])
            out.setdefault(e['oid'], nm)
    for oid, nm in EXTRA.items():
        out.setdefault(oid, nm)
    return out


def patch(bsn, snn, tg):
    bp = os.path.join(ROOT, bsn)
    orig = bp + '.orig'
    if not os.path.exists(orig):
        with open(bp, 'rb') as f:
            raw = f.read()
        with open(orig, 'wb') as f:
            f.write(raw)
        print('  备份 %s -> %s.orig (%d B)' % (bsn, bsn, len(raw)))
    with open(orig, 'rb') as f:
        d = bytearray(f.read())
    assert len(d) == R * NREC
    with open(os.path.join(ROOT, snn), 'rb') as f:
        flags = f.read()[0x14:0x14 + NREC]
    assert len(flags) == NREC

    sched, n_susp, n_keep = {}, 0, 0
    for oid in range(NREC):
        rec = d[oid * R: (oid + 1) * R]
        w = struct.unpack_from('<H', rec, 0x27)[0]
        birth = 1490 + (w & 0x7f)
        old_app = 1560 + ((w >> 7) & 0x3f)
        name = s7(rec, 0) + s7(rec, 7)
        if flags[oid]:                       # 剧本已登场: 不动
            n_keep += 1
            continue
        if oid in tg:
            new_app = min(1623, max(1561, birth + GENPEUKU_AGE))
            sched.setdefault(new_app, []).append('%s(id%d,生%d)' % (tg[oid], oid, birth))
        else:
            new_app = 1560 + SUSPEND
            n_susp += 1
        if new_app == old_app:
            continue
        w = (w & ~0x1F80) | (((new_app - 1560) & 0x3f) << 7)   # 只清/置 bits7..12, 生年与高3位原样保留
        struct.pack_into('<H', rec, 0x27, w)
        d[oid * R: (oid + 1) * R] = bytes(rec)                 # rec 是切片副本, 必须写回

    with open(bp, 'wb') as f:
        f.write(bytes(d))
    print('\n===== %s (剧本标志源 %s) =====' % (bsn, snn))
    n_app = sum(len(v) for v in sched.values())
    print('  剧本已登场(不动) %d | 目标提前登场 %d | 其余挂起到 1623 %d' % (n_keep, n_app, n_susp))
    tot = 0
    for y in sorted(sched):
        print('   %d 登场: %s' % (y, '、'.join(sched[y])))
        tot += len(sched[y])
    print('  合计 %d 人进入动态登场日程(待登场槽容量 141)' % tot)
    return sched


def main():
    tg = target_oids()
    print('目标集(族谱 exact/alias + 官方待登场档案): %d 个 oid' % len(tg))
    for bsn, snn in PAIRS:
        patch(bsn, snn, tg)
    print('\nOK: BSDATA 登场年已改写。实机若异常 -> 把 *.TR2.orig 覆盖回 *.TR2 即完全还原。')


if __name__ == '__main__':
    main()
