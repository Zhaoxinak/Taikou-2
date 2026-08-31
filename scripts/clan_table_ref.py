#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SNDATA S1 武将名 + S4 势力（大名家）表 ✅ 续103

两条关键发现：
 1. **S1 实体池（370 × 59B）内嵌 GBK 姓名**：`rec[0..6]` = 姓(7B)、`rec[7..13]` = 名(7B)，
    均以 0 结尾。由此可**直接从剧本流读出全部 370 个武将名**，无需 BSDATA 索引映射
    （实体索引 ≠ BSDATA 索引：实测仅 5/370 同名，二者是两套编号）。
 2. **S4 的 49 条是「势力/大名家」不是「国」**：`rec[0]` = 本拠（城/町索引）→ 经城表 `+0x08`
    反查所属国；`rec[1]` = **国主武将号**；`rec[2]` = **有效标志**（0=有效，1=占位/未初始化）。
    49 条按本领国**从北到南单调排序**，一个大国内可有多个势力（故不是 0..48 的排列）。
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STREAM_BASE = 0x58C
N_ENTITY, ENTITY_STRIDE = 370, 59
N_CASTLE, CASTLE_STRIDE = 200, 26
N_PROV, PROV_STRIDE = 49, 5          # S3 国情基表（在城表与势力表之间，勿漏）
N_CLAN, CLAN_STRIDE = 49, 11
OFF_ENTITY = 22
OFF_CASTLE = OFF_ENTITY + N_ENTITY * ENTITY_STRIDE            # 21852
OFF_PROV = OFF_CASTLE + N_CASTLE * CASTLE_STRIDE              # 27052
OFF_CLAN = OFF_PROV + N_PROV * PROV_STRIDE                    # 27297

# 历史锚点：**记录序号** -> 该剧本应有的大名（注意不是国号）
HISTORY = {
    0: '南部晴政', 1: '伊达晴宗', 2: '大崎义直', 3: '最上义守', 4: '芦名盛氏',
    5: '上杉谦信', 6: '北条氏康', 7: '宇都宫广纲', 8: '佐竹义昭', 9: '里见义尧',
    10: '武田信玄', 11: '今川氏真', 12: '德川家康', 13: '织田信长', 14: '斋藤龙兴',
    15: '北田具教', 16: '本愿寺显如', 17: '神保长职', 18: '田山义续', 19: '朝仓义景',
    20: '浅井长政', 21: '六角承侦', 22: '松永久秀', 23: '筒井顺庆', 24: '足利义辉',
    25: '三好长庆', 26: '波多野宗长', 27: '杂贺佐太夫', 28: '别所长胜', 29: '小寺政职',
    30: '山名佑丰', 31: '尼子义久', 32: '宇喜多直家',
}


def gbk7(b):
    s = b.split(b'\x00')[0]
    try:
        return s.decode('gbk')
    except Exception:
        return ''


def decode(fn):
    data = open(os.path.join(ROOT, fn), 'rb').read()
    key = data[0x12] ^ data[0x13]
    return bytes(x ^ key for x in data[STREAM_BASE:])


def main():
    ok = fail = 0
    def chk(l, cond):
        nonlocal ok, fail
        if cond: ok += 1; print(f'  [PASS] {l}')
        else:    fail += 1; print(f'  [FAIL] {l}')

    print('=== S1 武将名 + S4 势力表（续103） ===')
    chk('实体池偏移 = 22', OFF_ENTITY == 22)
    chk('城表偏移 = 22 + 370*59', OFF_CASTLE == 22 + 370 * 59)
    chk('国情基表偏移 = 城表后', OFF_PROV == OFF_CASTLE + 200 * 26)
    chk('势力表偏移 = 国情基表后 = 27297', OFF_CLAN == 27297)

    out = {}
    for sc, fn in (('scenario1', 'Taikou2 Original/SNDATA1.TR2'),
                   ('scenario2', 'Taikou2 Original/SNDATA2.TR2')):
        s = decode(fn)
        E = s[OFF_ENTITY:OFF_ENTITY + N_ENTITY * ENTITY_STRIDE]
        CS = s[OFF_CASTLE:OFF_CASTLE + N_CASTLE * CASTLE_STRIDE]
        CL = s[OFF_CLAN:OFF_CLAN + N_CLAN * CLAN_STRIDE]
        names = [gbk7(E[59 * i:59 * i + 7]) + gbk7(E[59 * i + 7:59 * i + 14])
                 for i in range(N_ENTITY)]
        print(f'\n--- {sc} ---')
        chk('370 个武将名非空率 ≥ 90%',
            sum(1 for n in names if n) >= 370 * 0.9)
        chk('织田信长在名表中', any('织田信长' == n for n in names))

        prov_of = lambda ci: CS[26 * ci + 3] if ci != 0xff else None
        rows = []
        for i in range(N_CLAN):
            r = CL[11 * i:11 * i + 11]
            rows.append({'rec': i, 'home': r[0], 'prov': prov_of(r[0]),
                         'lord': r[1], 'valid': r[2] == 0,
                         'w06': int.from_bytes(r[3:5], 'little')})
        ps = [x['prov'] for x in rows if x['prov'] is not None]
        # 「按本领国排序」是剧本1 的性质；剧本2 年代不同、格局不同，不强制
        if sc == 'scenario1':
            chk('势力表按本领国单调不减排序（从陆奥到萨摩）', ps == sorted(ps))
        else:
            print(f'  [INFO] {sc} 国号序列(不强制单调): {ps}')
        chk('国号覆盖数 ≥ 30（非 0..48 排列，一国内可有多势力）',
            len(set(ps)) >= 30)
        chk('rec[2]=0 的记录国主全部可解析为武将名',
            all(names[x['lord']] for x in rows if x['valid']))

        if sc == 'scenario1':
            # 历史锚点校验
            bad = []
            for rec_i, expected in HISTORY.items():
                got = names[rows[rec_i]['lord']] if rows[rec_i]['valid'] else None
                if got != expected:
                    bad.append((rec_i, expected, got))
            chk(f'历史锚点 {len(HISTORY)} 个大名全部正确', not bad)
            if bad:
                for b in bad[:8]: print(f'      国{b[0]}: 期望{b[1]} 实得{b[2]}')

        out[sc] = {'entity_names': names,
                   'clans': [dict(x, lord_name=names[x['lord']] if x['lord'] < 370 else '')
                             for x in rows]}

    json.dump(out, open(os.path.join(ROOT, 'scripts/clan_table.json'), 'w',
                        encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n==== {ok} PASS / {fail} FAIL ====')
    print('saved scripts/clan_table.json')
    return 0 if fail == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
