#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
太閤立志伝2 · EXE 静态段中文名表全集（合戦 + 城池 + 外交）
==========================================================
2026-08-27 深夜（续6）破解。来源：脱壳映像 `_unpacked_mem.bin`（base 0x400000）。

破解方法（教训驱动）
------------------
过去把「兵种/阵形/計略名」判为「不在 EXE 静态段」，是因为只扫了
`0x506ca8`/`0x504800`/`0x507b58` 几张**大表**。本轮改为**全段无先验扫描**
（`_string_pool_scan.py`：0x500000–0x530000 全部 GBK 串 → 按地址间隙分池 →
等距 stride 检测），一次性挖出 9 张定长名表，其中包含长期缺口「兵种名」。

⚠️ 阵形名：全段 2014 条 CJK 串中**没有任何**日式阵形名（鱼鳞/鹤翼/雁行/方圆/
锋矢/长蛇/偃月/车悬 全部 0 命中，「阵」只出现在剧情文与「阵亡∶」）。
⇒ 结论：**太阁2 合戦没有玩家可见的阵形名**，`byte[p+4]`(0..3) 是内部布阵编号。

用法：
  python scripts/static_name_tables.py            # 自校验 + 打印
  python scripts/static_name_tables.py --json     # 写 static_name_tables.json
"""
from __future__ import annotations

import json
import os
import sys

BASE = 0x400000
_HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(_HERE, '_unpacked_mem.bin')
OUT = os.path.join(_HERE, 'static_name_tables.json')

# ============================================================ 表定义 ======
# (键, 基址, stride, 条数, 说明, 访问器)
TABLES = [
    # ---- 合戦 ----
    ('unit_types', 0x50bfe8, 5, 3,
     '兵种名（byte[unit+0x13] & 3 → 0=步兵 1=骑兵 2=洋枪；3=空/城守备）',
     '0x43e140 类别=byte[unit+0x13]&3 → 0x43e150 名=&0x50bfe8[cls*5]'),
    ('unit_type_menu', 0x509a48, 16, 3,
     '兵种选择菜单项（带对齐空格）', 'UI 菜单串池'),
    ('corps_slots', 0x5037e0, 7, 5,
     '部队槽名（对应布阵表 5 个单位槽，slot0=主将）',
     '0x42fd38 / 0x430e12：idx*8-idx = idx*7 + 0x5037e0'),
    ('battle_facilities', 0x503818, 7, 5,
     '战场设施名（对应设施标记实例表 0x513a78，5B×16）', 'stride 7'),
    ('sides', 0x503808, 8, 2,
     '阵营名（0=敌人 1=盟军）；选择位 byte[unit+0x15] & 8',
     '0x43e170 单位显示名格式化器'),
    ('corps_attrs_a', 0x5099d8, 5, 4,
     '部队编成列名 A（统御/武力/骑马/洋枪）', '0x4823a1 → UI 0x4b1700'),
    ('corps_attrs_b', 0x509a78, 5, 5,
     '部队编成列名 B（统御/武力/兵法/马术/洋枪）', '0x482ded（func 0x482d50）'),
    ('tactics', 0x5032d8, 7, 11,
     '計略名（handler 表 0x503328）', '见 deployment_tactics_ref.py'),
    # ---- 城池 / 国情面板 ----
    ('castle_fields', 0x50953c, 8, 10,
     '城池状态字段名', '0x47ccb6 push 0x50953c（循环绘制，行索引 bp）'),
    ('rating_words', 0x50b6ba, 9, 24,
     '评价形容词 = 8 组 × 3 档（低/中/高），与 castle_fields 配对显示',
     '池基址被间接引用（无直接绝对立即数 xref）'),
    # ---- 外交 ----
    ('persuade_methods', 0x502858, 16, 6,
     '说服/劝降手段', 'stride 16'),
]

# 期望值（逐字节自校验用）
EXPECT = {
    'unit_types': ['步兵', '骑兵', '洋枪'],
    'unit_type_menu': ['  步  兵  ', '  骑  兵  ', '  洋枪队  '],
    'corps_slots': ['总大将', '第二军', '第三军', '第四军', '第五军'],
    'battle_facilities': ['本城', '米仓', '了望台', '哨所', '城门'],
    'sides': ['敌人', '盟军'],
    'corps_attrs_a': ['统御', '武力', '骑马', '洋枪'],
    'corps_attrs_b': ['统御', '武力', '兵法', '马术', '洋枪'],
    'tactics': ['鼓　舞', '伏　兵', '伪　兵', '谣　言', '火　计', '开　城',
                '挑　衅', '落　石', '牵　制', '修　复', '填　埋'],
    'castle_fields': ['士　气', '训练度', '防御度', '支持率', '俸  禄',
                      '军  马', '洋  枪', '士兵数', '军　粮', '军资金'],
    'rating_words': ['缺乏', '丰富', '富强', '低', '普通', '高',
                     '缺乏', '足够', '充裕', '薄弱', '普通', '坚固',
                     '缺乏', '充实', '强大', '缺少', '丰富', '无数',
                     '稚嫩', '普通', '精干', '低', '精神', '勇敢'],
    'persuade_methods': ['诱之以利', '诱之以官禄', '劝其报复',
                         '以亡国论劝说', '一味劝说', '描述信长'],
}

# 兵种类别映射表 0x50bfd0（24B，值 0..3），访问器 0x4a0b00
UNIT_TYPE_MAP_VA = 0x50bfd0
UNIT_TYPE_MAP_N = 24

# 募兵/购买金额阶梯 0x50bfb8（word × 10 = 1000..25000）
MONEY_LADDER_VA = 0x50bfb8
MONEY_LADDER_N = 10
# 前置购买档 0x50bfa0：3 × 8B = (dword id, word 金额, word 数量)
PURCHASE_TIERS_VA = 0x50bfa0
PURCHASE_TIERS_N = 3


def load():
    with open(IMG, 'rb') as f:
        return f.read()


def read_table(mem, va, stride, n):
    out = []
    for i in range(n):
        raw = mem[va - BASE + i * stride: va - BASE + i * stride + stride]
        s = raw.split(b'\x00')[0]
        try:
            out.append(s.decode('gbk'))
        except UnicodeDecodeError:
            out.append(repr(s))
    return out


def main():
    mem = load()
    ok = True
    result = {'_source': 'TAIK2W95.exe (unpacked) static .data', '_base': hex(BASE),
              'tables': {}}

    print('=== 静态段中文名表逐字节自校验 ===')
    for key, va, stride, n, desc, accessor in TABLES:
        vals = read_table(mem, va, stride, n)
        exp = EXPECT[key]
        # 评价词表尾部有对齐空格，比较时 strip
        norm = [v.replace('\u3000', '\u3000').strip() for v in vals]
        expn = [e.strip() for e in exp]
        good = norm == expn
        ok &= good
        print(f'  [{"OK" if good else "FAIL"}] {key:<18s} {va:#08x} stride={stride:<2d} n={n:<2d} {desc}')
        if not good:
            print(f'         image  {norm}')
            print(f'         expect {expn}')
        result['tables'][key] = {
            'va': hex(va), 'stride': stride, 'count': n,
            'desc': desc, 'accessor': accessor,
            'values': vals,
        }

    # 评价词重排成 8 组 × 3 档
    rw = result['tables']['rating_words']['values']
    groups = [[rw[g * 3 + k].strip() for k in range(3)] for g in range(8)]
    result['rating_word_groups'] = groups
    print('\n=== 评价词 8 组 × 3 档（低 / 中 / 高）===')
    for gi, g in enumerate(groups):
        print(f'  组{gi}  {g[0]:<4s} / {g[1]:<4s} / {g[2]:<4s}')

    # 兵种类别映射
    m = list(mem[UNIT_TYPE_MAP_VA - BASE: UNIT_TYPE_MAP_VA - BASE + UNIT_TYPE_MAP_N])
    result['unit_type_map'] = {'va': hex(UNIT_TYPE_MAP_VA), 'count': UNIT_TYPE_MAP_N,
                              'accessor': '0x4a0b00 = movzx eax, byte[eax+0x50bfd0]',
                              'values': m}
    print(f'\n=== 兵种类别映射表 {UNIT_TYPE_MAP_VA:#x}（访问器 0x4a0b00）===\n  {m}')
    print('  分组：[0..3]=3  [4..7]=0  [8..15]=1  [16..19]=2  [20..23]=3')

    # 金额阶梯
    import struct
    ladder = list(struct.unpack_from('<10H', mem, MONEY_LADDER_VA - BASE))
    result['money_ladder'] = {'va': hex(MONEY_LADDER_VA), 'values': ladder,
                             'desc': 'word × 10 金额阶梯（募兵/购买菜单候选额）'}
    tiers = [list(struct.unpack_from('<IHH', mem, PURCHASE_TIERS_VA - BASE + i * 8))
             for i in range(PURCHASE_TIERS_N)]
    result['purchase_tiers'] = {'va': hex(PURCHASE_TIERS_VA),
                               'layout': '(dword id, word 金额, word 数量)',
                               'tiers': tiers}
    print(f'\n=== 金额阶梯 {MONEY_LADDER_VA:#x} (word×10) ===\n  {ladder}')
    print(f'=== 购买档 {PURCHASE_TIERS_VA:#x} (id, 金额, 数量) ===\n  {tiers}')
    assert ladder == [1000, 2000, 3000, 4000, 6000, 8000, 10000, 15000, 20000, 25000], ladder
    assert tiers == [[4, 5000, 50], [5, 10000, 100], [6, 30000, 200]], tiers
    print('  [OK] 金额阶梯 & 购买档 数值断言通过')

    result['formation_names'] = {
        'status': 'NOT_IN_EXE',
        'note': '全段 2014 条 CJK 串零命中日式阵形名（鱼鳞/鹤翼/雁行/方圆/锋矢/长蛇/偃月/车悬）；'
                '「阵」仅见于剧情文与「阵亡∶」。⇒ 太阁2 合戦无玩家可见阵形名，'
                'byte[p+4](0..3) 是内部布阵编号（→ 相克矩阵 0x5031d0）。',
    }

    if '--json' in sys.argv:
        with open(OUT, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f'\n[写出] {OUT}')

    print('\n结果：' + ('全部自校验通过 ✅' if ok else '存在不一致 ❌'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
