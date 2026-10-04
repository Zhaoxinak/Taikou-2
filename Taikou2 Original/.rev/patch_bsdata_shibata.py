# -*- coding: utf-8 -*-
"""
patch_bsdata_shibata.py — 给 BSDATA1/2.TR2 补 5 名柴田一门史实武将 (槽 695-699)

设计约束(见 bsdata_format.json / export_for_godot.py):
  * 59B/record, 700 条; 0x10 字段 bushou_id 必须 == 记录号(解码器不变式).
  * 名表仅 436 槽 / 实体池仅 370 槽, id 695-699 超出 -> 原生 UI 空名崩溃.
    故新武将**保持休眠**: 不写 SNDATA 登场标志(默认 0), 不进场景, 不占实体.
  * 仅作数据落地(家族树/列表已自包含, 这里让她们"在阵营里"有数据支撑).

策略: 克隆一条已知良好记录(柴田胜家 id1), 仅改写下列偏移, 其余字节原样保留:
  0x00-0x06 姓(7B GBK NUL 填充)   0x07-0x0d 名(7B)
  0x10-0x11 bushou_id=u16         0x16-0x1a 五维 u8x5
  0x1b-0x1d 10 技能 x2bit(u8x3)    0x27 生年-1490
  0x29-0x2a 父 id=u16(0xffff=无)   0x30 国  0x31 城
  0x32-0x33 功勋 u16              0x34 俸禄 u8  0x35 忠诚 u8
  0x36-0x37 主君 u16(0xffff=浪人)  0x39 职位=byte&7  0x3a 高4位=archetype
"""
import struct, os, sys
sys.stdout.reconfigure(encoding='utf-8')

BASE = r'F:\Games\Taikou 2\Taikou2 Original'
RSIZE, NREC = 59, 700
RANK = ['无', '足轻组头', '足轻工头', '足轻头', '家老', '组头', '家臣', '大名']

# 槽位 -> 新武将定义
#   (姓, 名, 生年, 父id, 国, 城, 功勋, 俸禄, 忠诚, 主君, 职位, archetype, 五维, 技能)
NEW = {
    695: ('柴田', '胜政', 1524, 0xFFFF, 13, 66, 4000, 150, 79, 1,    4, 5, [80,78,60,50,65], None),
    696: ('',     '阿市', 1547, 0xFFFF, 13, 66,    0,   0, 100, 13,   6, 4, [40,30,70,75,90], b'\x00\x00\x00'),
    697: ('浅井', '茶茶', 1567, 0xFFFF, 13, 66,    0,   0, 100, 13,   6, 4, [35,25,60,60,88], b'\x00\x00\x00'),
    698: ('浅井', '初',   1570, 0xFFFF, 13, 66,    0,   0, 100, 13,   6, 4, [35,25,65,70,85], b'\x00\x00\x00'),
    699: ('浅井', '江',   1573, 0xFFFF, 13, 66,    0,   0, 100, 13,   6, 4, [35,25,60,75,90], b'\x00\x00\x00'),
}

TEMPLATE_ID = 1  # 柴田胜家(已知良好记录)


def s7(raw, off):
    return raw[off:off + 7].split(b'\x00')[0]


def decode(raw, i):
    return dict(idx=i, sur=s7(raw, 0).decode('gbk', 'replace'),
               giv=s7(raw, 7).decode('gbk', 'replace'),
               bushou=struct.unpack_from('<H', raw, 0x10)[0],
               forces=list(raw[0x16:0x1b]), birth=raw[0x27] + 1490,
               father=struct.unpack_from('<H', raw, 0x29)[0],
               prov=raw[0x30], city=raw[0x31],
               merit=struct.unpack_from('<H', raw, 0x32)[0],
               salary=raw[0x34], loyalty=raw[0x35],
               lord=struct.unpack_from('<H', raw, 0x36)[0],
               rank=raw[0x39] & 7, archetype=raw[0x3a] >> 4)


def patch_record(rec, spec):
    sur, giv, birth, father, prov, city, merit, salary, loy, lord, rank, arch, forces, skills = spec
    # 姓 / 名 (7B, GBK, NUL 填充)
    sb = (sur.encode('gbk') + b'\x00' * 7)[:7]
    gb = (giv.encode('gbk') + b'\x00' * 7)[:7]
    rec[0:7] = sb
    rec[7:14] = gb
    # 五维
    for k, v in enumerate(forces):
        rec[0x16 + k] = v & 0xFF
    # 技能(可选覆盖)
    if skills is not None:
        rec[0x1b:0x1e] = skills[:3]
    # 生年
    rec[0x27] = (birth - 1490) & 0xFF
    # 父
    struct.pack_into('<H', rec, 0x29, father)
    # 国 / 城
    rec[0x30] = prov
    rec[0x31] = city
    # 功勋
    struct.pack_into('<H', rec, 0x32, merit)
    # 俸禄 / 忠诚
    rec[0x34] = salary & 0xFF
    rec[0x35] = loy & 0xFF
    # 主君
    struct.pack_into('<H', rec, 0x36, lord)
    # 职位(低3位)
    rec[0x39] = (rec[0x39] & 0xF8) | (rank & 7)
    # archetype(高4位)
    rec[0x3a] = ((arch & 0xF) << 4) | (rec[0x3a] & 0x0F)
    return rec


def main():
    for fn in ('BSDATA1.TR2', 'BSDATA2.TR2'):
        path = os.path.join(BASE, fn)
        data = bytearray(open(path, 'rb').read())
        assert len(data) == RSIZE * NREC, (fn, len(data))
        tmpl = data[TEMPLATE_ID * RSIZE:(TEMPLATE_ID + 1) * RSIZE]
        print('===== %s =====' % fn)
        print('  模板(柴田胜家 id1): 姓=%s 名=%s bushou=%d 五维=%s 相性=%s 技能=%s'
              % (s7(tmpl,0).decode('gbk','replace'), s7(tmpl,7).decode('gbk','replace'),
                 struct.unpack_from('<H', tmpl, 0x10)[0], list(tmpl[0x16:0x1b]),
                 struct.unpack_from('<H', tmpl, 0x14)[0], tmpl[0x1b:0x1e].hex()))
        for idx, spec in NEW.items():
            rec = bytearray(tmpl)              # 克隆模板(保留未知字节)
            # 先覆盖内容
            patch_record(rec, spec)
            # 再强制 bushou_id == 记录号(不变式)
            struct.pack_into('<H', rec, 0x10, idx)
            data[idx * RSIZE:(idx + 1) * RSIZE] = rec
            o = decode(rec, idx)
            print('  写入 #%-3d %s%s 生%d 父%d 国%d 城%s 功勋%d 忠%d 主君%d 职位%s arch%d 五维%s'
                  % (idx, o['sur'], o['giv'], o['birth'], o['father'], o['prov'],
                     o['city'] if o['city']!=255 else '浪人', o['merit'], o['loyalty'],
                     o['lord'] if o['lord']!=0xFFFF else '浪人', RANK[o['rank']], o['archetype'], o['forces']))
            assert o['bushou'] == idx, 'bushou_id 不变式失败: %d != %d' % (o['bushou'], idx)
        # 自检: 695-699 全部存在且 bushou_id 正确, 且确实未改 SNDATA(本脚本只动 BSDATA)
        for idx in NEW:
            rr = data[idx*RSIZE:(idx+1)*RSIZE]
            assert struct.unpack_from('<H', rr, 0x10)[0] == idx
        open(path, 'wb').write(bytes(data))
        print('  已写回 %s (%d B)\n' % (fn, len(data)))


if __name__ == '__main__':
    main()
