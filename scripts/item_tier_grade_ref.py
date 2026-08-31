# -*- coding: utf-8 -*-
r"""
item_tier_grade_ref.py — 物品 tier 分档规则 + 孤品身份码（续115）

============================================================================
🔑 结论：tier 不是由 val / cat 公式算出的，而是**手工历史声望评级**
============================================================================

证据（均在本文件 self-test 中可复跑）：

1. **非单调（排除公式）**：19 个含 ≥3 件的「27类 cat」中，**15 个类内 tier 与 val 非单调**
   （例：同是刀剑 cat7，三日月宗近 val37 → tier2，吉冈一文字 val38 → tier0；
   助真作太刀 val23 → tier2，大刀长船伦光 val42 → tier0）。
   ⇒ tier 绝不可能是 `f(val)` 或 `f(cat)`，否则必单调。

2. **数值天然分三档区间**（与 flag 完美耦合，见续112）：
   - **A 和物（日式传统名物主流）** → tier **0..5**（覆盖 cat 0..16,18,19,20,26）
   - **B 南蛮/工芸系** → tier **9,10**（cat 12,14,16,17,20,22,23,24,25,26）
   - **C 絵画系** → tier **19,20**（**仅** cat 18,19,20；self-test 断言 100% 命中）
   - ⇒ 三档在 cat 空间**重叠**（同一 cat 可跨档），进一步证明是作者手工声望分级，
      而非按类目自动算出的「品级」。

3. **通用分界 + 五孤品身份码**（flag=0x00 组 21 件 / flag=0xff 组 1 件）：
   - tier **11** = 通用/名物分界（17 件共用：珠光小茄子/初花茶罐/富士茄子…）
   - tier ∈ {**89, 126, 165, 202, 255**} = **5 件唯一孤品/特产的硬编码身份码**
     （数值本身无分级意义，仅作 identity 区分）：
     | tier | 物品 | cat | val | 备注 |
     |------|------|-----|-----|------|
     | 89   | 基石金   | 14 | 50  | 金块 |
     | 126  | 佐渡金   | 14 | 30  | 金块 |
     | 165  | 孙子秘本 | 12 | 200 | 兵法書，val 满 |
     | 202  | 古天明平蜘蛛 | 5 | 105 | 名茶釜 |
     | 255  | 吴子秘本 | 12 | 200 | 全表唯一孤品(flag=0xff) |

总 tier 取值集合 = {0,1,2,3,4,5,9,10,11,19,20,89,126,165,202,255} = **16 个**（与续112 一致）。

============================================================================
⚠️ 与「定价」的关系（重要）
============================================================================
- `price = getValue(grp&7, val, (grp>>3)&0xf)`（续113）—— **定价只读 grp&7 / SUB / val**，
  **完全不读 tier**。tier 是「收藏/声望」维度的评级，与买卖价值正交。
- 因此「tier 高分=更贵」是错觉：村正 val49→tier0（最贵却 tier0），
  吴子秘本 val200→tier255（最贵书却 tier255 身份码）。两者维度不同。
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# 全 16 个合法 tier 值
KNOWN_TIERS = {0, 1, 2, 3, 4, 5, 9, 10, 11, 19, 20, 89, 126, 165, 202, 255}

# 5 件孤品身份码 → (物品名, cat, val)
SENTINEL = {
    89:  ('基石金', 14, 50),
    126: ('佐渡金', 14, 30),
    165: ('孙子秘本', 12, 200),
    202: ('古天明平蜘蛛', 5, 105),
    255: ('吴子秘本', 12, 200),
}

# flag → 合法 tier 集合（续112 分区，本文件复核）
FLAG_TIER = {
    0x80: {0, 1, 2, 3, 4, 5, 9, 10, 19, 20},   # 名物珍宝 178 件
    0x00: {11, 89, 126, 165, 202},               # 通用交易品 21 件
    0xff: {255},                                 # 孤品 1 件
}

# 三家族数值区间
FAMILY_RANGE = {
    'A_和物': range(0, 6),
    'B_南蛮工芸': (9, 10),
    'C_絵画': (19, 20),
}


def family_of(tier):
    if 0 <= tier <= 5:
        return 'A_和物(0-5)'
    if tier in (9, 10):
        return 'B_南蛮工芸(9-10)'
    if tier in (19, 20):
        return 'C_絵画(19-20)'
    if tier == 11:
        return 'D_通用分界(11)'
    if tier in SENTINEL:
        return 'E_孤品身份码(%d)' % tier
    return '???'


def _self_test():
    with open(os.path.join(HERE, 'item_table_200.json'), encoding='utf-8') as f:
        data = json.load(f)
    ok = fail = 0

    def chk(name, cond, extra=''):
        nonlocal ok, fail
        if cond:
            ok += 1
        else:
            fail += 1
            print('  [FAIL] %s %s' % (name, extra))

    chk('共 200 件', len(data) == 200, str(len(data)))

    seen = set()
    for it in data:
        t = int(it['tier'])
        fl = int(it['flag'])
        cat = int(it['cat'])
        val = int(it['val'])
        seen.add(t)
        chk('tier %d 在 16 已知值内' % t, t in KNOWN_TIERS, str(it['name']))
        chk('flag %#x 的分区含 tier %d' % (fl, t), t in FLAG_TIER.get(fl, set()), str(it))

    chk('恰 16 个不同 tier 值', len(seen) == 16, str(sorted(seen)))

    # 五孤品身份码逐一命中
    for t, (nm, c, v) in SENTINEL.items():
        hits = [it for it in data if int(it['tier']) == t]
        chk('tier %d = %s' % (t, nm), len(hits) == 1 and hits[0]['name'] == nm, str(hits))
        if hits:
            chk('  └ cat/val 吻合', int(hits[0]['cat']) == c and int(hits[0]['val']) == v)

    # 絵画家族纯净性：tier19/20 仅出现在 cat∈{18,19,20}
    paint = [int(it['cat']) for it in data if int(it['tier']) in (19, 20)]
    chk('tier19/20 仅 cat{18,19,20}(絵画)', paint and all(c in (18, 19, 20) for c in paint), str(sorted(set(paint))))

    # 非单调验证（排除公式）：统计类内 tier/val 非单调的 cat 数
    from collections import defaultdict
    bycat = defaultdict(list)
    for it in data:
        bycat[int(it['cat'])].append((int(it['tier']), int(it['val'])))
    nonmono = 0
    big = 0
    for c, rows in bycat.items():
        if len(rows) < 3:
            continue
        big += 1
        s = sorted(rows)
        mono = True
        for (t1, v1), (t2, v2) in zip(s, s[1:]):
            if (t1 < t2 and v1 > v2) or (t1 > t2 and v1 < v2):
                mono = False
        if not mono:
            nonmono += 1
    chk('多条目类内 tier/val 非单调 (>=10/%d)' % big, nonmono >= 10, '%d/%d' % (nonmono, big))

    # 家族区间自洽
    for it in data:
        t = int(it['tier'])
        fam = family_of(t)
        if t in (9, 10):
            chk('B 家族 t%d' % t, fam.startswith('B_'))
        elif t in (19, 20):
            chk('C 家族 t%d' % t, fam.startswith('C_'))
        elif 0 <= t <= 5:
            chk('A 家族 t%d' % t, fam.startswith('A_'))

    print('\nitem_tier_grade_ref self-test: %d OK, %d FAIL' % (ok, fail))
    return 1 if fail else 0


if __name__ == '__main__':
    raise SystemExit(_self_test())
