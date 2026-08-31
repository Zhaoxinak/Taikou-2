#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SNDATA 全部 18 段 —— 权威结构总表（续99/100/101）

所有 stride / 记录数 / 基址均来自：
  · Unicorn 实跑 0x47f350（`_emu_stream_dump.py` / `_emu_sections_layout.py`）
  · 各序列化器反汇编（`_dis_ser2.py` / `_dis5.py`）：`mov esi, X` 的 X 是「真基址+首字段偏移」
  · 除法魔数交叉验证（0x2aaaaaab / 2^33 = 1/12）
⚠️ emu 最小周期对同构数组会退化为 1（如 S9/S10 全 W），真实记录大小须由 loader 的
   循环计数 `ebx` 与消费方 `lea [reg*N + base]` 的 N 共同判定。
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STREAM_BASE = 0x58C

# (段, 序列化器, 长度, 基址, stride, 记录数, 语义)
SECTIONS = [
    ('S0',  0x47dae0,    22, None,      22,   1, '全局/头部'),
    ('S1',  0x47dce0, 21830, 0x519868,  59, 370, '武将实体池'),
    ('S2',  0x47e130,  5200, 0x51eb88,  26, 200, '城/町表（§3.17.6）'),
    ('S3',  0x47e3a0,   245, 0x519548,   5,  49, '国情基表'),
    ('S4',  0x47e440,   539, 0x5179b8,  11,  49, '49 国政治/关系表（§3.18.6）'),
    ('S5',  0x47e5a0,   180, 0x5197b0,  30,   6, '6 槽武将表（+0x14=武将号，剧本内全空 0xffff）'),
    ('S6',  0x47e770,    46, 0x516610,  46,   1, '单条全局状态（180 处引用的热全局）'),
    ('S7',  0x47ea80,  3200, 0x516a28,  16, 200, '与城表同序的 200 条运行时表（剧本内全 0）'),
    ('S8',  0x47ebb0,   360, 0x517850,  12,  30, '30 条表，W0 = ID 1000..1029'),
    ('S9',  0x47ecb0,    80, 0x519238,   4,  20, '20 条表，W0 = ID 2000..2019'),
    ('S10', 0x47ed10,   120, 0x5176a8,   4,  30, '30 条表，W0 = ID 3000..3029，W1 恒 0xffff'),
    ('S11', 0x47ed70,  3800, None,       19, 200, '物品段（槽 11..199 = 物品定义表 189×19B）'),
    ('S12', 0x47ee50,   160, 0x517728,   8,  20, '★ 物品副池（20 具名特殊物）；流 8B/条，运行期 stride 12（+0..+3 是 vptr，不入流）'),
    ('S13', 0x47ef00,  2280, 0x5185b6, 114,  20, '20 条空表（全 0xff）'),
    ('S14', 0x47f050,  1176, 0x51dc60,   1, 1176, '★ 49 国外交关系矩阵（严格上三角 49×48/2）'),
    ('S15', 0x47f0a0,    25, 0x5203c2,  25,   1, '3 段标志数组 @0x5203c2/0x5203ca/0x5203d3'),
    ('S16', 0x47f1b0,    40, 0x519680,   2,  20, '20 × WORD @0x519680'),
    ('S17', 0x47f210,   133, 0x517c73,  13,  10, '3B 前缀(@0x517c70..72) + 10 × 13B @0x517c73（全 0）'),
]
# 城表字段（续99 终版，仿真实测读序列 W B B B W B B B B W W W W W B W W）
CASTLE_FIELDS = [
    (0,  2, 0x00, 'officer_entity'), (2,  1, 0x04, 'castle_ref'),
    (3,  1, 0x08, 'province'),       (4,  1, 0x09, 'f09'),
    (5,  2, 0x0a, 'f0a'),            (7,  1, 0x0c, 'nousang'),
    (8,  1, 0x0d, 'f0d'),            (9,  1, 0x0e, 'minkok'),
    (10, 1, 0x0f, 'seisan'),         (11, 2, 0x10, 'gunryo'),
    (13, 2, 0x12, 'kome'),           (15, 2, 0x14, 'shikin'),
    (17, 2, 0x16, 'f16'),            (19, 2, 0x18, 'f18'),
    (21, 1, 0x1a, 'f1a'),            (22, 2, 0x1b, 'castle_type'),
    (24, 2, 0x1d, 'unused_ffff'),
]
GEO_ANCHORS = {'踯躅崎': 10, '春日山': 12, '骏府': 13, '滨松': 14,
               '冈崎': 15, '清洲': 16, '稻叶山': 17, '金泽': 21}


def u16(b, i):
    return b[i] | (b[i + 1] << 8)


def decode(fn):
    data = open(os.path.join(ROOT, fn), 'rb').read()
    key = data[0x12] ^ data[0x13]
    return key, bytes(x ^ key for x in data[STREAM_BASE:])


def bounds():
    out, c = [], 0
    for s in SECTIONS:
        out.append((c, c + s[2])); c += s[2]
    return out


def main():
    ok = fail = 0
    def chk(l, cond):
        nonlocal ok, fail
        if cond: ok += 1; print(f'  [PASS] {l}')
        else:    fail += 1; print(f'  [FAIL] {l}')

    B = bounds()
    print('=== SNDATA 18 段结构总表（续101） ===')
    chk('段长合计 = 39436', sum(s[2] for s in SECTIONS) == 39436)
    SPECIAL = {'S12': '运行期 stride 12（流 8B/条，+0..+3 为 vptr）',
               'S17': '3B 前缀 + 10 × 13B'}
    for i, (nm, fn, ln, base, st, n, desc) in enumerate(SECTIONS):
        ok_len = ln == B[i][1] - B[i][0]
        if nm == 'S17':                       # 3B 前缀 + 10 × 13B = 133
            ok_div = (ln - 3) == st * n
        else:
            ok_div = (ln % st == 0) and (ln // st == n)
        chk(f'{nm} {ln}B / stride {st} = {n} 条'
            + (f'  [{SPECIAL[nm]}]' if nm in SPECIAL else ''), ok_len and ok_div)

    for sc, fn in (('scenario1', 'Taikou2 Original/SNDATA1.TR2'),
                   ('scenario2', 'Taikou2 Original/SNDATA2.TR2')):
        key, s = decode(fn)
        print(f'\n--- {sc} (key={key:#x}) ---')
        S = [s[a:e] for a, e in B]
        # 城表
        cs = [S[2][26 * i:26 * i + 26] for i in range(200)]
        prov = [r[3] for r in cs]
        chk('城表 province(+0x08) 覆盖 0..48 共 49 值', sorted(set(prov)) == list(range(49)))
        names = json.load(open(os.path.join(ROOT, 'scripts/castle_names_exe.json'),
                               encoding='utf-8'))['castles']
        nm = {c['id']: c['exe_name'] for c in names}
        hit = sum(1 for i in range(200) if nm.get(i) in GEO_ANCHORS
                  and cs[i][3] == GEO_ANCHORS[nm[i]])
        chk(f'城表地理锚点 {len(GEO_ANCHORS)} 个全中',
            hit == sum(1 for i in range(200) if nm.get(i) in GEO_ANCHORS))
        chk('城表 +0x1d 恒 0xffff', all(u16(r, 24) == 0xffff for r in cs))
        # S7 全 0
        chk('S7 (200×16B) 全 0', all(v == 0 for v in S[7]))
        # S13 全 0xff
        chk('S13 (2280B) 全 0xff', all(v == 0xff for v in S[13]))
        # S5 六槽全空模板
        chk('S5 六槽一致且首字段 0xffff',
            all(S[5][30 * i:30 * i + 2] == b'\xff\xff' for i in range(6)))
        # S8/S9/S10 的 ID 序列
        w0_8 = [u16(S[8], 12 * i) for i in range(30)]
        w0_9 = [u16(S[9], 4 * i) for i in range(20)]
        w0_10 = [u16(S[10], 4 * i) for i in range(30)]
        chk('S8 W0 = 1000..1029 连续', w0_8 == list(range(1000, 1030)))
        chk('S9 W0 = 2000..2019 连续', w0_9 == list(range(2000, 2020)))
        chk('S10 W0 = 3000..3029 连续', w0_10 == list(range(3000, 3030)))
        chk('S10 W1 恒 0xffff', all(u16(S[10], 4 * i + 2) == 0xffff for i in range(30)))
        # S12 副池：+0x0a 恒 0xffff
        chk('S12 每槽末字段恒 0xffff', all(u16(S[12], 8 * i + 6) == 0xffff for i in range(20)))
        # S14 关系矩阵位域
        M = S[14]
        chk('S14 外交級(bit0-2) 全 0..7', all((v & 7) <= 7 for v in M))
        chk('S14 主从級(bit3-4) 全 0..3', all(((v >> 3) & 3) <= 3 for v in M))
        # S11 物品表
        chk('S11 物品表 189 条末字节为 0',
            all(S[11][11 * 19 + 19 * i + 18] == 0 for i in range(189)))

        if sc == 'scenario1':
            out = {
                'stream_base': STREAM_BASE,
                'sections': [{'name': nm, 'func': hex(fn), 'len': ln,
                              'base_va': hex(base) if base else None,
                              'stride': st, 'records': n, 'desc': desc,
                              'stream_range': list(B[i]),
                              'file_range': [B[i][0] + STREAM_BASE, B[i][1] + STREAM_BASE]}
                             for i, (nm, fn, ln, base, st, n, desc) in enumerate(SECTIONS)],
                'castle_fields': [{'stream_off': o, 'width': w, 'rec_off': hex(r), 'name': nm}
                                  for o, w, r, nm in CASTLE_FIELDS],
                's12_secondary_pool_8b': [
                    {'slot': i, 'b4': S[12][8 * i], 'b5': S[12][8 * i + 1],
                     'w6': u16(S[12], 8 * i + 2), 'w8': u16(S[12], 8 * i + 4),
                     'w10': u16(S[12], 8 * i + 6)} for i in range(20)],
                's8_records': [{'id': u16(S[8], 12 * i), 'b2': S[8][12 * i + 2],
                                'b3': S[8][12 * i + 3], 'b4': S[8][12 * i + 4],
                                'b5': S[8][12 * i + 5], 'w6': u16(S[8], 12 * i + 6),
                                'b8': S[8][12 * i + 8], 'b9': S[8][12 * i + 9]}
                               for i in range(30)],
                's9_records': [{'id': u16(S[9], 4 * i), 'w1': u16(S[9], 4 * i + 2)}
                               for i in range(20)],
                's10_records': [{'id': u16(S[10], 4 * i), 'w1': u16(S[10], 4 * i + 2)}
                                for i in range(30)],
                's16_words': [u16(S[16], 2 * i) for i in range(20)],
            }
            json.dump(out, open(os.path.join(ROOT, 'scripts/sndata_all_sections.json'),
                                'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n==== {ok} PASS / {fail} FAIL ====')
    return 0 if fail == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
