#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SNDATA 剧本流 —— 权威段落表 + 城表字段映射 + 物品表定位（续99）

Ground truth 全部来自 Unicorn 实跑主解析器 0x47f350（scripts/_emu_stream_dump.py）：
逐次挂钩 0x47da10 记录真实消费的字节，按序列化器归属分段。

🔴 三条对旧文档的关键纠偏：
 1. 流基址 = 文件偏移 **0x58C (1420)**，不是 0x598 (1432)。
    主解析器在首次 refill 前读 0x10+2+2+0x2bc+0x2bc = 1420B 头部。
 2. 城表块起点 = 流 **21852** = 22(全局) + 21830(实体池 370x59)。
    旧记的 21852/21845 都是在错误基址上的坐标，二者皆非。
 3. 城表**所属国 = +0x08(BYTE, stream[3])**，不是旧记的 +0x16。
    8/8 地理锚点命中（踯躅崎=10 甲斐 / 春日山=12 越後 / 骏府=13 / 滨松=14 /
    冈崎=15 / 清洲=16 / 稻叶山=17 / 金泽=21）。
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STREAM_BASE = 0x58C          # 1420  —— 纠偏后的真流基址
N_ENTITY, ENTITY_STRIDE = 370, 59
N_CASTLE, CASTLE_STRIDE = 200, 26

# 主解析器 0x47f350 的 18 个序列化器（call 顺序即流顺序）
SERIALIZERS = [
    0x47dae0, 0x47dce0, 0x47e130, 0x47e3a0, 0x47e440, 0x47e5a0,
    0x47e770, 0x47ea80, 0x47ebb0, 0x47ecb0, 0x47ed10, 0x47ed70,
    0x47ee50, 0x47ef00, 0x47f050, 0x47f0a0, 0x47f1b0, 0x47f210,
]
# Unicorn 实跑实测长度（字节）
SEC_LEN = [22, 21830, 5200, 245, 539, 180, 46, 3200, 360, 80,
           120, 3800, 160, 2280, 1176, 25, 40, 133]
SEC_NAME = ['global', 'entity_pool', 'castle', 'province_base', 'province_politics',
            'unk5', 'unk6', 'unk7', 'unk8', 'unk9', 'unk10',
            'item_defs_200x19', 'unk12_20x8', 'unk13_all_ff', 'unk14_49x24',
            'unk15_flag25', 'unk16_20xword', 'eof_padding']

# 城表：仿真实测读序列 W B B B W B B B B W W W W W B W W = 9*2+8 = 26B
# (流字节, 宽, 记录偏移, 语义)
CASTLE_FIELDS = [
    (0,  2, 0x00, 'officer_entity'),   # <0x172 -> x47 + 0x519868 ; 0xffff = 空缺
    (2,  1, 0x04, 'castle_ref'),       # <0xc8 -> x31 + 0x51eb88 ; 0xff = 无
    (3,  1, 0x08, 'province'),         # ✅ 所属国 0..48（49 distinct，地理锚点全中）
    (4,  1, 0x09, 'f09'),
    (5,  2, 0x0a, 'f0a'),              # 与 officer_entity 同值（第二处实体引用）
    (7,  1, 0x0c, 'nousang'),          # 农商 0..40
    (8,  1, 0x0d, 'f0d'),              # 0..250（守城/次级）
    (9,  1, 0x0e, 'minkok'),           # 民心 0..200
    (10, 1, 0x0f, 'seisan'),           # 生产率 0..100
    (11, 2, 0x10, 'gunryo'),           # 军粮
    (13, 2, 0x12, 'kome'),             # 米
    (15, 2, 0x14, 'shikin'),           # 资金
    (17, 2, 0x16, 'f16'),
    (19, 2, 0x18, 'f18'),
    (21, 1, 0x1a, 'f1a'),              # 0..200
    (22, 2, 0x1b, 'castle_type'),      # &7 = 城种
    (24, 2, 0x1d, 'unused_ffff'),      # 恒 0xffff
]
# 地理锚点（城名 -> 国号），用于自校验 province
GEO_ANCHORS = {'踯躅崎': 10, '春日山': 12, '骏府': 13, '滨松': 14,
               '冈崎': 15, '清洲': 16, '稻叶山': 17, '金泽': 21}

ITEM_TABLE_SLOT0 = 11        # S11 内物品表起始槽位（前 11 槽为另一 19B 结构）
ITEM_N, ITEM_STRIDE = 189, 19

# 每段「读宽序列」（续100，由 _emu_sections_layout.py 按调用方地址统计 B/W 得出）
# (段序, 长度, 周期字节, 周期宽序列, 记录数)  —— W=WORD(2B) B=BYTE(1B)
SECTION_LAYOUT = [
    (0,    22,  22, 'BBBBBBWWWWWWBBW',   1),      # 全局
    (1, 21830,  59, 'BBBBBBBBBBBBBBWWWWBBBBBBBBBBBBBBWBWWBBBBBBBWBBWWB', 370),
    (2,  5200,  26, 'WBBBWBBBBWWWWWBWW', 200),    # 城/町表
    (3,   245,   5, 'BBBW',              49),     # 国情基表
    (4,   539,  11, 'BWWBBBBBB',         49),     # 49 国政治表
    (5,   180,  30, 'WWWWWWWBBWBBWWWWW',  6),
    (6,    46,  46, 'WWWWWWWBBWBBWWWWWWWWWWWWW', 1),
    (7,  3200,  16, 'BBWWWWWBBBB',      200),
    (8,   360,  12, 'WWBBBBWBB',         30),
    (9,    80,   2, 'W',                 40),
    (10,  120,   2, 'W',                 60),
    (11, 3800,  19, 'BBBBBBBBBBBBBBBWW', 200),    # 物品段
    (12,  160,   8, 'BBWWW',             20),
    (13, 2280, 114, 'W' * 55 + 'BBBB',   20),     # 空表(全 0xff)
    (14, 1176,   1, 'B',               1176),     # 平坦 blob @0x51dc60
    (15,   25,   1, 'B',                 25),     # 标志数组
    (16,   40,   2, 'W',                 20),
    (17,  133,   1, 'B',                133),     # EOF 填充
]


def u16(b, i):
    return b[i] | (b[i + 1] << 8)


def decode(fn):
    data = open(os.path.join(ROOT, fn), 'rb').read()
    key = data[0x12] ^ data[0x13]
    return key, bytes(x ^ key for x in data[STREAM_BASE:])


def sections(stream):
    out, c = [], 0
    for i, L in enumerate(SEC_LEN):
        out.append(stream[c:c + L]); c += L
    return out


def parse_castle(rec):
    d = {}
    for off, w, ro, name in CASTLE_FIELDS:
        d[name] = u16(rec, off) if w == 2 else rec[off]
    return d


def main():
    ok = fail = 0
    def chk(label, cond):
        nonlocal ok, fail
        if cond: ok += 1; print(f'  [PASS] {label}')
        else:    fail += 1; print(f'  [FAIL] {label}')

    print('=== SNDATA 段落表（Unicorn 实跑 0x47f350） ===')
    sec_off, c = [], 0
    for i, L in enumerate(SEC_LEN):
        sec_off.append((c, c + L)); c += L
    chk('段长合计 = 39436', sum(SEC_LEN) == 39436)
    chk('流基址 = 0x58C(1420)', STREAM_BASE == 1420)
    chk('城表起点 = 22 + 370*59 = 21852',
        sec_off[2][0] == 22 + N_ENTITY * ENTITY_STRIDE)
    chk('城表 = 200 * 26B', SEC_LEN[2] == N_CASTLE * CASTLE_STRIDE)
    chk('实体池 = 370 * 59B', SEC_LEN[1] == N_ENTITY * ENTITY_STRIDE)
    chk('国情基表 = 49 * 5B', SEC_LEN[3] == 245)
    chk('49国政治表 = 49 * 11B', SEC_LEN[4] == 539)
    chk('物品段 = 200 * 19B', SEC_LEN[11] == 200 * ITEM_STRIDE)
    chk('物品表 = 189 * 19B 且落在 S11 末端',
        ITEM_TABLE_SLOT0 * ITEM_STRIDE + ITEM_N * ITEM_STRIDE == SEC_LEN[11])
    chk('S14 可分解为 49 * 24B', SEC_LEN[14] == 49 * 24)
    chk('EOF 填充段存在', SEC_LEN[17] == 133)

    print('\n--- 读宽序列自校验（续100，按调用方地址统计 B/W）---')
    for idx, ln, pb, pat, rows in SECTION_LAYOUT:
        w = sum(2 if c == 'W' else 1 for c in pat)
        chk(f'S{idx} 周期 {pb}B = {pat.count("W")}W+{pat.count("B")}B'
            f' × {rows} 条',
            w == pb and SEC_LEN[idx] == ln and (ln % pb == 0) and (ln // pb == rows))

    for sc, fn in (('scenario1', 'Taikou2 Original/SNDATA1.TR2'),
                   ('scenario2', 'Taikou2 Original/SNDATA2.TR2')):
        key, s = decode(fn)
        print(f'\n--- {sc} (key={key:#x}, 流长 {len(s)}) ---')
        secs = sections(s)
        castle = secs[2]
        recs = [parse_castle(castle[26 * i:26 * i + 26]) for i in range(200)]

        prov = [r['province'] for r in recs]
        chk('province(+0x08) 覆盖 0..48 共 49 值',
            sorted(set(prov)) == list(range(49)))
        chk('officer_entity 有效(<=369 或 0xffff)',
            all(v <= 369 or v == 0xffff for v in
                (r['officer_entity'] for r in recs)))
        chk('minkok 0..200', all(0 <= r['minkok'] <= 200 for r in recs))
        chk('seisan 0..100', all(0 <= r['seisan'] <= 100 for r in recs))
        chk('f0d 0..250', all(0 <= r['f0d'] <= 250 for r in recs))
        chk('unused_ffff 恒 0xffff', all(r['unused_ffff'] == 0xffff for r in recs))
        chk('castle_type &7 <= 7', all((r['castle_type'] & 7) <= 7 for r in recs))

        cn = json.load(open(os.path.join(ROOT, 'scripts/castle_names_exe.json'),
                            encoding='utf-8'))['castles']
        name = {c['id']: c['exe_name'] for c in cn}
        hit = 0
        for i, r in enumerate(recs):
            if name.get(i) in GEO_ANCHORS:
                hit += (r['province'] == GEO_ANCHORS[name[i]])
        chk(f'地理锚点 {len(GEO_ANCHORS)} 个全中',
            hit == sum(1 for i in range(200) if name.get(i) in GEO_ANCHORS))

        # 物品表
        s11 = secs[11]
        items = [list(s11[ITEM_TABLE_SLOT0 * ITEM_STRIDE + ITEM_STRIDE * i:
                           ITEM_TABLE_SLOT0 * ITEM_STRIDE + ITEM_STRIDE * (i + 1)])
                 for i in range(ITEM_N)]
        chk('物品表 189 条末字节为 0', all(it[18] == 0 for it in items))

        if sc == 'scenario1':
            out = {
                'stream_base': STREAM_BASE,
                'sections': [{'idx': i, 'func': '0x%x' % SERIALIZERS[i],
                              'name': SEC_NAME[i], 'len': SEC_LEN[i],
                              'stream_range': list(sec_off[i]),
                              'file_range': [sec_off[i][0] + STREAM_BASE,
                                             sec_off[i][1] + STREAM_BASE]}
                             for i in range(len(SEC_LEN))],
                'castle_fields': [{'stream_off': o, 'width': w, 'rec_off': '0x%02x' % r,
                                   'name': n} for o, w, r, n in CASTLE_FIELDS],
                'castle': recs,
                'item_table_offset_in_S11': ITEM_TABLE_SLOT0 * ITEM_STRIDE,
                'castle_names': {str(i): name.get(i) for i in range(200)},
            }
            with open(os.path.join(ROOT, 'scripts/sndata_sections.json'), 'w',
                      encoding='utf-8') as f:
                json.dump(out, f, ensure_ascii=False, indent=1)

    print(f'\n==== {ok} PASS / {fail} FAIL ====')
    return 0 if fail == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
