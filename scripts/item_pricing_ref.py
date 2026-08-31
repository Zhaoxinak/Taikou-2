# -*- coding: utf-8 -*-
r"""
item_pricing_ref.py — 物品字段重释义 + 定价模型全静态闭合（续113）

============================================================================
★ 核心结论：物品定价无需 emu，全部可由静态定义数据算出
============================================================================
getValue(0x49c070) 只读两个字段（live 反汇编坐实）：

    word [item+8]  ->  CAT = &7 , SUB = (>>3)&0xf
    byte [item+5]  ->  LEVEL

而序列化器 `0x47ed70` 的写入是：

    BYTE -> 表 +5   <- 流[14]  (旧称 val)
    WORD -> 表 +8   <- 流[17..18] (旧称 grp|pad)

⇒ 🔴 **字段重释义**：

| 流偏移 | 旧称（续73/80）        | **正确含义**                                   |
|-------|----------------------|---------------------------------------------|
| `[13]`| cat (0..26)          | **细分类 27 类**（显示/归并用，**不参与定价**）   |
| `[14]`| val 「价值基准 1..200」 | **= LEVEL**（getValue 的等级输入）               |
| `[15]`| tier                 | 与 [16] 合成 **16-bit 复合稀有度字**（见 §3.19.8）|
| `[16]`| flag                 | 同上（高字节）                                  |
| `[17]`| grp 「系列/同类编号」   | **= CAT(bits0-2) \| SUB(bits3-6) \| OWNED(bit7)** |
| `[18]`| pad                  | 高字节（定义期多为 0）                           |

⇒ **定价公式**：`price = getValue(CAT, val, SUB)`，其中
`CAT = grp & 7`、`SUB = (grp >> 3) & 0xf`、`LEVEL = val`。

============================================================================
验证 1：grp&7 与续98 的 27→8 归并表比对 → 192/200 (96%) 吻合
============================================================================
8 个不吻合项**全是跨类特例，且 grp 更正确**（归并非纯按 cat，而是逐件由 grp 定）：

| slot | 名称 | cat | 归并表期望 CAT | grp | grp&7 | 说明 |
|------|------|-----|--------------|-----|-------|------|
| 80 | 世界图屏风 | 20 屏风 | 6 美术品 | 109 | **5 南蛮物** | 世界地图=南蛮主题 |
| 81 | 四都市图   | 20 屏风 | 6 美术品 | 109 | **5 南蛮物** | 同上 |
| 82 | 洋人奏乐图 | 20 屏风 | 6 美术品 | 229 | **5 南蛮物** | 洋人=南蛮主题 |
| 93 | 圣书       | 12 兵书 | 1 书籍   | 173 | **5 南蛮物** | 聖書=圣经→南蛮物 |
| 94 | 圣书       | 12 兵书 | 1 书籍   | 173 | **5 南蛮物** | 同上 |
| 95 | 绢织物     | 26 织物 | 2 道具   | 29  | **5 南蛮物** | |
| 97 | 绵织物     | 26 织物 | 2 道具   | 21  | **5 南蛮物** | |
| 138| 白檀沉香   | 26 织物·香 | 2 道具 | 107 | **3 财宝** | 香木→财宝 |

⇒ **grp 是权威的逐件 CAT/SUB**；续98 的 27→8 归并表是**按细分类的近似**（96% 正确），
在「西方主题物」「香木」等跨类情形会分错。

============================================================================
验证 2：算出的价格语义完全合理（无需 emu）
============================================================================
价格范围 **200 .. 19800**。最高/最低：

    19800 slot100 村正      (CAT4 SUB15 LEVEL49)   ← 最有名的刀
    19200 slot101 正宗      (CAT4 SUB15 LEVEL46)
    17600 slot102 千手院长吉 (CAT4 SUB14 LEVEL43)
    16400 slot103 大刀长船伦光(CAT4 SUB13 LEVEL42)
    14800 slot104 菊一文字  (CAT4 SUB12 LEVEL39)
    14400 slot105 三日月宗近(CAT4 SUB12 LEVEL37)
    14200 slot110 村雨      (CAT4 SUB10 LEVEL46)
    12400 slot  1 九十九茄子 (CAT7 SUB15 LEVEL155)  ← 名物茶入
      ...
      200 slot199 斗战经    (CAT1 SUB1 LEVEL10)    ← 兵书
      200 slot 98 香水      (CAT5 SUB1 LEVEL3)
      200 slot133 小柄      (CAT4 SUB1 LEVEL1)

名刀最贵、兵书杂物最贱 —— 与游戏常识一致 ⇒ 定价模型闭合。

============================================================================
与「商品基价」的关系（两套不同尺度，勿混）
============================================================================
* 本文件 `getValue(CAT,val,SUB)` = **物品自身价值**（200..19800），用于买卖/茶会估价。
* `item_base_price.py` 的 `base_price = val // 10`（0..20）= **商店基价档位**，
  是另一套（更小尺度）的定价。两者**都用 `val`**，但用途不同。

============================================================================
字段在位态：定义态 vs 实例态
============================================================================
    +4  定义: cat(0..26 细分类)     → 实例: scratch/数量
    +5  定义: val = LEVEL           → 实例: LEVEL（**同义，不被覆盖**）
    +6  定义: tier | flag<<8        → 实例: OWNER_KEY（被覆盖）
    +8  定义: grp | pad<<8 = CAT|SUB|OWNED → 实例: FLAGS（**同义，不被覆盖**）

⇒ **+5 与 +8 在定义期即已是最终语义**，这正是定价可全静态求解的原因。
   grp 的 bit7 = OWNED（实测 121/200 置位；定义期取值，实例期会被改写）。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ---- 续98 的 27→8 归并表（用于交叉验证）----
DEF_CAT_TO_POOL_CAT = {
    0: 7, 1: 7, 2: 7, 3: 7, 4: 7, 5: 7,          # 茶器 -> 茶具
    6: 4, 7: 4, 8: 4, 9: 4, 10: 4,                # 武具 -> 武器
    11: 1, 12: 1, 13: 1,                          # 书籍 -> 书籍
    14: 3, 15: 3, 16: 3, 17: 3,                   # 财宝 -> 财宝
    18: 6, 19: 6, 20: 6,                          # 美术 -> 美术品
    22: 5, 23: 5, 24: 5, 25: 5,                   # 南蛮 -> 南蛮物
    26: 2,                                        # 织物香 -> 道具
}

# 8 个「grp 更正确」的跨类特例：(slot, name, cat, 归并表CAT, grp, grp&7)
CROSS_CAT_EXCEPTIONS = [
    (80, '世界图屏风', 20, 6, 109, 5),
    (81, '四都市图', 20, 6, 109, 5),
    (82, '洋人奏乐图', 20, 6, 229, 5),
    (93, '圣书', 12, 1, 173, 5),
    (94, '圣书', 12, 1, 173, 5),
    (95, '绢织物', 26, 2, 29, 5),
    (97, '绵织物', 26, 2, 21, 5),
    (138, '白檀沉香', 26, 2, 107, 3),
]

POOL_CAT_NAMES = ['酒', '书籍', '道具', '财宝', '武器', '南蛮物', '美术品', '茶具']


def predict_value(cat, level, sub):
    """Mirror of getValue (0x49c070) —— 与 item_pool_bind_ref 同式。"""
    if cat == 0:
        return max(min(level, 0xfa), 1)
    if cat == 1:
        return max(min((level + sub * 10) * 10, 0x1964), 0xa)
    if cat == 2:
        return max(min(level * 20, 0x1388), 0x14)
    if cat == 3:
        return max(min((level + sub * 50) * 10, 0x7ef4), 0x64)
    if cat == 4:
        adj = (sub - 5) if sub > 5 else 0
        return max(min((level + adj * 5) * 200, 0xea60), 0xc8)
    return max(min((level * (sub + 5)) << 2, 0xc350), 0xc8)


def cat_of(item):
    return item['grp'] & 7


def sub_of(item):
    return (item['grp'] >> 3) & 0xf


def owned_of(item):
    return bool(item['grp'] & 0x80)


def price_of(item):
    """price = getValue(CAT, val(=LEVEL), SUB)"""
    return predict_value(cat_of(item), item['val'], sub_of(item))


def _self_test():
    ok = fail = 0

    def chk(name, cond, extra=''):
        nonlocal ok, fail
        if cond:
            ok += 1
        else:
            fail += 1
            print(f"  [FAIL] {name} {extra}")

    # --- 归并表自身 ---
    chk('归并表值域 0..7', all(0 <= v <= 7 for v in DEF_CAT_TO_POOL_CAT.values()))
    chk('8 个类目名', POOL_CAT_NAMES == ['酒', '书籍', '道具', '财宝', '武器', '南蛮物', '美术品', '茶具'])
    chk('8 个跨类特例', len(CROSS_CAT_EXCEPTIONS) == 8)

    # --- 打包/解包自洽 ---
    for grp in (0x00, 0xFF, 0x7F, 0x6D, 0xE7):
        c, s, o = grp & 7, (grp >> 3) & 0xf, bool(grp & 0x80)
        chk(f'grp {grp:#04x} 解包', 0 <= c <= 7 and 0 <= s <= 15)

    p = 'scripts/item_table_200.json'
    if not os.path.exists(p):
        print(f"  [SKIP] 缺少 {p}")
    else:
        items = json.load(open(p, encoding='utf-8'))
        chk('200 件', len(items) == 200, f'got {len(items)}')

        # val = LEVEL 的取值合法性
        chk('val ∈ 1..200', all(1 <= x['val'] <= 200 for x in items))
        chk('grp ∈ 0..255', all(0 <= x['grp'] <= 255 for x in items))
        chk('CAT ∈ 0..7', all(0 <= cat_of(x) <= 7 for x in items))
        chk('SUB ∈ 0..15', all(0 <= sub_of(x) <= 15 for x in items))

        # 归并表交叉验证：192 匹配 / 8 例外
        mism = []
        for x in items:
            exp = DEF_CAT_TO_POOL_CAT.get(x['cat'])
            if exp is None:
                continue
            if cat_of(x) != exp:
                mism.append((x['slot'], x['name'], x['cat'], exp, x['grp'], cat_of(x)))
        chk('不吻合恰 8 件', len(mism) == 8, f'got {len(mism)}: {mism[:4]}')
        chk('不吻合项与登记表一致',
            sorted(m[:2] for m in mism) == sorted(e[:2] for e in CROSS_CAT_EXCEPTIONS),
            f'got {sorted(m[:2] for m in mism)}')
        print(f"  归并表吻合 {200 - len(mism)}/200，跨类特例 {len(mism)} 件（grp 更正确）")

        # 价格语义
        prices = [(price_of(x), x['slot'], x['name']) for x in items]
        prices.sort(reverse=True)
        chk('价格范围 200..19800',
            min(p[0] for p in prices) == 200 and max(p[0] for p in prices) == 19800,
            f"got {min(p[0] for p in prices)}..{max(p[0] for p in prices)}")
        chk('最贵 = 村正', prices[0][2] == '村正', f'got {prices[0][2]}')
        chk('次贵 = 正宗', prices[1][2] == '正宗', f'got {prices[1][2]}')
        top5 = {n for _, _, n in prices[:5]}
        chk('前 5 全为名刀',
            top5 == {'村正', '正宗', '千手院长吉', '大刀长船伦光', '菊一文字'}, f'got {top5}')
        print(f"  最贵 5 件: {[f'{n}({v})' for v, _, n in prices[:5]]}")
        print(f"  最便宜 5 件: {[f'{n}({v})' for v, _, n in prices[-5:]]}")

        # OWNED 位
        n_owned = sum(1 for x in items if owned_of(x))
        chk('OWNED 置位 121 件', n_owned == 121, f'got {n_owned}')

        # 与商品基价是两套尺度（都源自 val，但不同用途）
        chk('基价档位 0..20', all(0 <= x['val'] // 10 <= 20 for x in items))

    print(f"\nitem_pricing_ref self-test: {ok} OK, {fail} FAIL")
    return 1 if fail else 0


if __name__ == '__main__':
    raise SystemExit(_self_test())
