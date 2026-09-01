# -*- coding: utf-8 -*-
"""
item_tier_ref.py — 物品定义表 `tier`(idx15) 与 `flag`(idx16) 语义 + 双池初始化（续112）

结论先行：
  ★ **`tier` 不是公式，是静态枚举数据**（全表仅 16 个取值）。
  ★ **`tier` 与 `flag` 完美耦合** ⇒ `流[15]`/`流[16]` 应视为一个 **16-bit 复合稀有度字**，
    低字节(tier)的含义随高字节(flag)的类别而变。

============================================================================
1. tier × flag 完美分区（实测 200 件，无例外）
============================================================================
| flag  | 类别（续80 命名）   | tier 取值                          | 件数 |
|-------|--------------------|------------------------------------|------|
| 0x80  | 名物珍宝           | 0,1,2,3,4,5,9,10,19,20（≤20 小值） | 178  |
| 0x00  | 通用交易品         | 11, 89, 126, 165, 202              | 21   |
| 0xff  | 传世孤品           | 255                                 | 1    |

⚠️ 注意 **tier=11 是分界**：它只出现在 flag=0x00 组（17 件），**不出现在名物组**；
故「通用交易品」是 21 件而非 4 件 —— 其中 17 件共用 tier=11，
另 4 件各占 89/126/165/202 中的一个。

⇒ 两字段**不是独立的**：flag 决定 tier 的量级区间。因此把 `[15]` 单独称作
「等级/稀有度评分」是误导；正确理解是 **word@+6 = tier | (flag<<8)**，即运行期
物品记录偏移 +6 的那个 word 正是这复合稀有度字（序列化器 `0x47ed70` 的
`WORD -> [edi+1]` = 表 +6）。

五件非 0x80 项（全表仅此 5 件）：

| slot | 名称       | cat | val | tier | flag |
|------|-----------|-----|-----|------|------|
| 2    | 古天明平蜘蛛 | 5   | 105 | 202  | 0x00 |
| 139  | 基石金     | 14  | 50  | 89   | 0x00 |
| 152  | 佐渡金     | 14  | 30  | 126  | 0x00 |
| 155  | 孙子秘本   | 12  | 200 | 165  | 0x00 |
| 156  | 吴子秘本   | 12  | 200 | 255  | 0xff |

（`吴子秘本` 是全表唯一的 flag=0xff 传世孤品。）

============================================================================
2. tier 的分布（名物组内）
============================================================================
    0:21  1:21  2:24  3:23  4:22  5:14  9:12  10:15  11:17  19:14  20:12
（另有 4 件大值 89/126/165/202 + 1 件 255）
⇒ 0..5 / 9..10 / 19..20 是名物组的三段连续小值；**11 单独属通用组（17 件共用）**。
  说明 tier 是**分档代号**，而非按价值排序的连续名次（同 cat 内 tier 与 val 非单调）。

============================================================================
3. 🆕 双池初始化 `0x47a390`（一处函数同时初始化两个池）
============================================================================
```asm
; ---- 主物品池 ----
mov eax, 0x51e1f0          ; 基址
mov ecx, 0xc8              ; 200 槽
lp1: mov dword [eax], 0x4fc0e0   ; vptr
     add eax, 0xa                ; ★ stride 10
     dec ecx; jne lp1
     ret
; ---- 副池（具名特殊物）----
mov eax, 0x517728          ; 基址
mov ecx, 0x14              ; 20 槽
lp2: mov dword [eax], 0x4fc0f0   ; vptr（注意与主池不同！）
     add eax, 0xc                ; ★ stride 12
     dec ecx; jne lp2
     ret
```
⇒ **主池 stride 10 / 200 槽的第 4 条独立证据**；同时坐实副池
`0x517728` stride 12 / 20 槽，且两池 **vptr 不同**（`0x4fc0e0` vs `0x4fc0f0`）
⇒ 是两套不同的 C++ 类。

============================================================================
4. 实例侧的「名物」判定
============================================================================
`0x45e2d1`：`and eax,7` / `cmp ax,1` / `cmp word[ecx-2], bx` / **`test dh, 0x80`** /
`lea eax,[ecx-8]`。其中 `test dh,0x80` 即检测 `+6` word 的**高字节 bit7** ——
与 flag=0x80（名物）一致 ⇒ 定义期的 flag 会**保留到实例中**并被用于「是否名物」判定
（续98 曾把 +6 记作 OWNER_KEY；两者是同一 word 的「定义态/实例态」两副语义，
与续111 §3.19.7 的口径统一）。

============================================================================
5. 仍未知
============================================================================
* tier 在「名物」档内 0..20 的具体分档规则（按品类？按流派 grp？）
* 4 件大值（89/126/165/202）与 255 的语义（疑为通用品/孤品的 getValue 输入 LEVEL）
* 需找到**创建物品实例**的函数（把 tier/flag/grp 转成实例 LEVEL/SUB）才能定案
"""
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>

import json
import os

# ---- 复合稀有度字的分区（实测，无例外）----
FLAG_NAMIMONO = 0x80    # 名物珍宝  -> tier <= 20
FLAG_GENERIC = 0x00     # 通用交易品 -> tier ∈ {11,89,126,165,202}
FLAG_UNIQUE = 0xff      # 传世孤品   -> tier == 255

GENERIC_TIERS = (11, 89, 126, 165, 202)
NAMIMONO_TIERS = (0, 1, 2, 3, 4, 5, 9, 10, 19, 20)
ALL_TIERS = (0, 1, 2, 3, 4, 5, 9, 10, 11, 19, 20, 89, 126, 165, 202, 255)  # 16 个

# 5 件非名物项（slot, name, cat, val, tier, flag）
NON_NAMIMONO = [
    (2, '古天明平蜘蛛', 5, 105, 202, 0x00),
    (139, '基石金', 14, 50, 89, 0x00),
    (152, '佐渡金', 14, 30, 126, 0x00),
    (155, '孙子秘本', 12, 200, 165, 0x00),
    (156, '吴子秘本', 12, 200, 255, 0xff),
]

# ---- 双池初始化常量（0x47a390）----
POOLS = {
    'main': dict(base=0x51e1f0, stride=0xa, count=0xc8, vptr=0x4fc0e0),
    'secondary': dict(base=0x517728, stride=0xc, count=0x14, vptr=0x4fc0f0),
}


def rarity_word(tier, flag):
    """word @ item+6 —— 序列化器把 流[15](tier) / 流[16](flag) 合成一个 word。"""
    return (tier & 0xff) | ((flag & 0xff) << 8)


def is_namimono(rword):
    """实例侧 0x45e2d1 的 `test dh,0x80` —— 高字节 bit7 即「名物」标志。"""
    return bool(rword & 0x8000)


def _self_test():
    ok = fail = 0

    def chk(name, cond, extra=''):
        nonlocal ok, fail
        if cond:
            ok += 1
        else:
            fail += 1
            print(f"  [FAIL] {name} {extra}")

    # --- 池常量 ---
    m, s = POOLS['main'], POOLS['secondary']
    chk('主池 stride 10', m['stride'] == 10)
    chk('主池 200 槽', m['count'] == 200)
    chk('主池末址', m['base'] + m['stride'] * m['count'] == 0x51E9C0)
    chk('副池 stride 12', s['stride'] == 12)
    chk('副池 20 槽', s['count'] == 20)
    chk('副池末址', s['base'] + s['stride'] * s['count'] == 0x517818)
    chk('两池 vptr 不同（两套 C++ 类）', m['vptr'] != s['vptr'])

    # --- 稀有度字 ---
    chk('名物字高位为 0x80', rarity_word(5, 0x80) == 0x8005)
    chk('孤品字为 0xffff', rarity_word(255, 0xff) == 0xFFFF)
    chk('is_namimono(0x8005)', is_namimono(0x8005))
    chk('非名物 0x00CA 判否', not is_namimono(0x00CA))

    # --- 真实数据 ---
    p = _ROOT + '/scripts/item_table_200.json'
    if not os.path.exists(p):
        print(f"  [SKIP] 缺少 {p}")
    else:
        items = json.load(open(p, encoding='utf-8'))
        chk('200 件', len(items) == 200, f'got {len(items)}')
        tiers = sorted({x['tier'] for x in items})
        chk('tier 恰 16 个取值', tiers == list(ALL_TIERS), f'got {tiers}')
        chk('tier 非连续评分（含大值）',
            max(tiers) == 255 and any(t > 20 for t in tiers))

        # 完美分区
        bad = []
        for x in items:
            f, t = x['flag'], x['tier']
            if f == 0x80 and t not in NAMIMONO_TIERS:
                bad.append(('0x80', x['slot'], t))
            elif f == 0x00 and t not in GENERIC_TIERS:
                bad.append(('0x00', x['slot'], t))
            elif f == 0xff and t != 255:
                bad.append(('0xff', x['slot'], t))
            elif f not in (0x00, 0x80, 0xff):
                bad.append(('flag?', x['slot'], f))
        chk('tier×flag 完美分区（无例外）', not bad, f'例外: {bad[:8]}')

        # flag 分布
        dist = {}
        for x in items:
            dist[x['flag']] = dist.get(x['flag'], 0) + 1
        chk('flag 仅 0x00/0x80/0xff', set(dist) <= {0, 0x80, 0xff}, f'got {dist}')
        chk('名物 178 件', dist.get(0x80) == 178, f"got {dist.get(0x80)}")
        chk('通用 21 件', dist.get(0x00) == 21, f"got {dist.get(0x00)}")
        chk('孤品 1 件', dist.get(0xff) == 1, f"got {dist.get(0xff)}")
        print(f"  flag 分布: {dist}")

        # 5 件非名物逐件核对
        for slot, nm, cat, val, tier, flag in NON_NAMIMONO:
            x = items[slot]
            chk(f'slot{slot} {nm}',
                (x['name'], x['cat'], x['val'], x['tier'], x['flag']) == (nm, cat, val, tier, flag),
                f"got {(x['name'], x['cat'], x['val'], x['tier'], x['flag'])}")

        # 名物件的复合字高位必须是 0x80
        chk('名物件复合字高位 0x80',
            all(is_namimono(rarity_word(x['tier'], x['flag'])) for x in items if x['flag'] == 0x80))

    print(f"\nitem_tier_ref self-test: {ok} OK, {fail} FAIL")
    return 1 if fail else 0


if __name__ == '__main__':
    raise SystemExit(_self_test())
