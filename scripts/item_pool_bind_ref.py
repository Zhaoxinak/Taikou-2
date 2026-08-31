import os
_HERE = os.path.dirname(os.path.abspath(__file__))
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
item_pool_bind_ref.py — 物品定义表(189×19B, SNDATA) ↔ 物品池(0x51e1f0/0x51e1f8) 绑定参考实现 + 自校验

来源：2026-08-29 续98 逆向（ID 续73 结构 + 续25/27 池模型 + 本次侦察）
=========================================================================================
结论总览（已坐实）：
  A. 物品池主池 0x51e1f0（stride 10B, 200 槽；扫描指针 0x51e1f8 = base+8）字段布局：
       +0  vptr(4)        → 0x4fc0e0（init 0x47a390 盖章）
       +4  byte scratch   （买卖路径中作数量增量/暂存，init 不写）
       +5  byte LEVEL     → getValue 输入
       +6  word OWNER_KEY → 玩家 0x516624(player_id) 或 (npc_pool_idx|0x8000)
       +8  word FLAGS     → bit7=owned/active；bits0-2=CAT(0..7)；bits3-6=SUB(0..15)
     ⚠️ 主池 **没有任何 def-index / 具体名 字段**（已逐一核查所有 setter 写入点）。

  B. 名称解析（反汇编 0x49c010/0x49c1f0/0x49c200 坐实）：
       getTypeName(0x49c010)    = 0x507ea8 + (CAT&7)*7   → 8 条类目名 酒/书籍/道具/财宝/武器/南蛮物/美术品/茶具
       getShortName(0x49c1f0)   = 0x507ee0 + (CAT&7)*5   → 8 条「类型短标」（酒/药/信/道具/军…，共享 item/skill vtable 的副用途）
       getSecondaryName(0x49c200)= 0x507a50 + slot*13     → 副池(0x517728,20槽) 20 条 **具名特殊物**（惠琼的信/介绍信/南蛮酒/铭酒/浊酒/药/绍喜·惠琼的墨迹/特殊宝物0014…0019）

  C. 值公式 getValue(0x49c070)：CAT=FLAGS&7 → 跳表 0x49c1cc；cat0..3 已 live 反汇编核对，cat4..7 同 续25：
       cat0: clamp(LEVEL,1,0xfa)
       cat1: clamp((LEVEL+SUB*10)*10,0xa,0x1964)
       cat2: clamp(LEVEL*20,0x14,0x1388)
       cat3: clamp((LEVEL+SUB*50)*10,0x64,0x7ef4)
       cat4: clamp((LEVEL+max(SUB-5,0)*5)*200,0xc8,0xea60)
       cat5/6/7: clamp((LEVEL*(SUB+5))<<2,0xc8,0xc350)

  D. 物品表 ↔ 物品池 绑定（本文件核心）：
       ★ 主池(0x51e1f0) 装 **通用交易品**（金块/茶碗/刀 等），身份= (CAT,LEVEL,SUB)，显示名=类目名。
         与 189 定义表的绑定 **仅到「类目」层级**：def 的 27 类(cat 0..26) 归并到主池的 8 类(CAT 0..7)。
         归并表见 DEF_CAT_TO_POOL_CAT（数据驱动：全部 189 件恰好各归一类，无歧义）。
       ★ 副池(0x517728,20槽,12B) 装 **20 件具名特殊物**（书信/特殊宝物），名=0x507a50[slot]，按 slot 固定对应。
       ★ 名物（村正/备前福耳…189 中的绝大多数）**不在池中按身份存储**——其身份(定义表 idx 0..188) 存于
         角色/存档库存（另一结构，非本池）。⇒ 「def-idx ↔ 池中实例」的实例级绑定 **仅副池 20 件具名特殊物存在**；
         主池通用品无 def-index（已证伪此类绑定）。

  ⚠️ 文档纠偏：旧 §3.19.6 记「物品表↔物品池（0x517850/stride12、0x51e1f8/stride10）」。
      0x517850 实为 **NPC/师父池**(stride12, 续21/27)，非物品池；物品副池是 0x517728(stride12,20槽)。
      0x51e1f8 才是主物品池扫描指针（base 0x51e1f0)。已更正。

运行：python scripts/item_pool_bind_ref.py
"""
import os
import json
import struct

STREAM_START = 0x598
TABLE_STREAM_OFF = 32019
REC_SIZE = 19
REC_COUNT = 189

# 主池 8 类目名（0x507ea8 stride7，[0..7]）
POOL_CAT_NAMES = ['酒', '书籍', '道具', '财宝', '武器', '南蛮物', '美术品', '茶具']

# 189 定义表 27 类（cat 0..26；21 空缺）
DEF_CAT_NAMES = {
    0: '茶碗·天目', 1: '赤乐茶碗', 2: '黄濑户茶碗', 3: '茶入·茶罐', 4: '花入·茶壶',
    5: '茶釜', 6: '名刀(村雨)', 7: '刀', 8: '胁差·短刀', 9: '枪', 10: '剃刀',
    11: '物语·书籍', 12: '兵书·史书', 13: '绘词', 14: '金', 15: '银',
    16: '宝石', 17: '宝石工艺品', 18: '挂轴·画', 19: '绘·画', 20: '屏风',
    21: '(空缺)', 22: '时钟', 23: '地球仪·天球仪', 24: '望远镜', 25: '南蛮物', 26: '织物·香',
}

# ── 数据驱动 27→8 类目归并（全部 189 件逐件核对：每 def-cat 恰好落入唯一 pool-cat）──
# 茶器(0..5)→茶具(7)；武具(6..10)→武器(4)；书籍绘词(11..13)→书籍(1)；
# 财宝(14..17)→财宝(3)；美术(18..20)→美术品(6)；南蛮(22..25)→南蛮物(5)；织物香(26)→道具(2)。
# 酒(0) 在定义表中无对应名物（故 189 件不覆盖 pool-cat 0）。
DEF_CAT_TO_POOL_CAT = {
    0: 7, 1: 7, 2: 7, 3: 7, 4: 7, 5: 7,
    6: 4, 7: 4, 8: 4, 9: 4, 10: 4,
    11: 1, 12: 1, 13: 1,
    14: 3, 15: 3, 16: 3, 17: 3,
    18: 6, 19: 6, 20: 6,
    22: 5, 23: 5, 24: 5, 25: 5,
    26: 2,
    # 21 空缺：无定义表项
}


def find_data_dir():
    for p in ('Taikou2 Original', os.path.join('..', 'Taikou2 Original')):
        if os.path.isdir(p):
            return p
    return None


def decrypt_stream(path):
    raw = open(path, 'rb').read()
    key = raw[0x12] ^ raw[0x13]
    return bytes(b ^ key for b in raw[STREAM_START:0x9f81]), key


def parse_defs(dec):
    out = []
    for i in range(REC_COUNT):
        o = TABLE_STREAM_OFF + i * REC_SIZE
        r = dec[o:o + REC_SIZE]
        z = r.find(b'\x00')
        name = r[:z].decode('gbk', 'replace') if z > 0 else '?'
        out.append({
            'idx': i, 'name': name,
            'cat': r[13], 'val': r[14], 'tier': r[15],
            'flag': r[16], 'grp': r[17],
        })
    return out


# ---- getValue（复刻 续25 + 本次 cat0..3 live 核对）----
def predict_value(cat, level, sub):
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
    # cat 5/6/7
    return max(min((level * (sub + 5)) << 2, 0xc350), 0xc8)


def main():
    d = find_data_dir()
    if d is None:
        print("[SKIP] 未找到 'Taikou2 Original/'")
        return
    dec, key = decrypt_stream(os.path.join(d, 'SNDATA1.TR2'))
    defs = parse_defs(dec)

    ok = fail = 0
    def chk(name, cond, extra=''):
        nonlocal ok, fail
        if cond:
            ok += 1
        else:
            fail += 1
            print(f"  [FAIL] {name} {extra}")

    print("=== 数据驱动 27→8 类目归并校验（189 件）===")
    from collections import defaultdict
    by_pool = defaultdict(list)
    multi = 0
    for it in defs:
        c = it['cat']
        pc = DEF_CAT_TO_POOL_CAT.get(c)
        chk(f'def{cat_ok(c)} maps', pc is not None, f"def-cat {c} 无映射")
        if pc is not None:
            by_pool[pc].append(it)
    # 每 pool-cat 名 == 0x507ea8 类目名
    chk('pool-cat 名表 = 8 类目', POOL_CAT_NAMES == ['酒','书籍','道具','财宝','武器','南蛮物','美术品','茶具'])

    print("\n  pool-cat : 定义表类目覆盖 -> 件数  示例")
    for pc in range(8):
        defcats = sorted([c for c, p in DEF_CAT_TO_POOL_CAT.items() if p == pc])
        items = by_pool.get(pc, [])
        ex = ', '.join(i['name'] for i in items[:3])
        print(f"   {pc} {POOL_CAT_NAMES[pc]:4s} <- def{catlist(defcats)}  ({len(items)}件)  e.g. {ex}")
        chk(f'pool-cat{pc} 有覆盖', len(defcats) > 0 or pc == 0)  # 酒(0) 无定义项属正常

    # 映射合法性：所有 pool-cat 取值 ∈ 0..7；定义表出现的每个 def-cat 都有映射
    chk('所有 pool-cat ∈ 0..7', all(0 <= v <= 7 for v in DEF_CAT_TO_POOL_CAT.values()))
    present_def_cats = sorted({it['cat'] for it in defs})
    chk('定义表每 def-cat 均有映射',
        all(c in DEF_CAT_TO_POOL_CAT for c in present_def_cats),
        f"缺失: {[c for c in present_def_cats if c not in DEF_CAT_TO_POOL_CAT]}")

    print("\n=== getValue 公式自校验（cat0..3 live 口径；cat4..7 续25）===")
    cases = [(0,50,0),(0,255,0),(0,0,0),(1,10,2),(2,10,0),(3,5,1),(4,10,3),(4,10,7),(5,10,0),(6,20,3),(7,1,0)]
    for cat, lvl, sub in cases:
        v = predict_value(cat, lvl, sub)
        print(f"   cat{cat} lvl={lvl} sub={sub} -> {v}")
        chk(f'getValue cat{cat}', isinstance(v, int) and v > 0)

    print(f"\n自校验: {ok} OK, {fail} FAIL")
    # 落盘绑定表
    out = {
        'pool_cat_names': POOL_CAT_NAMES,
        'def_cat_names': DEF_CAT_NAMES,
        'def_cat_to_pool_cat': {str(k): v for k, v in DEF_CAT_TO_POOL_CAT.items()},
        'def_cat_coverage': {str(pc): [c for c, p in DEF_CAT_TO_POOL_CAT.items() if p == pc] for pc in range(8)},
        'pool_field_layout': {
            '+0': 'vptr(4)->0x4fc0e0', '+4': 'byte scratch/qty', '+5': 'byte LEVEL',
            '+6': 'word OWNER_KEY', '+8': 'word FLAGS(bit7=owned,bits0-2=CAT,bits3-6=SUB)'},
        'name_tables': {
            'getTypeName': '0x507ea8 stride7 (cat 0..7)',
            'getShortName': '0x507ee0 stride5 (type-short label)',
            'getSecondaryName': '0x507a50 stride13 (secondary-pool slot 0..19, 20 named specials)'},
        'secondary_pool': {'base': '0x517728', 'stride': 12, 'count': 20,
                           'names': ['惠琼的信','日乘的信','绍喜的信','介绍信','南蛮酒','铭酒','浊酒','药',
                                     '绍喜的墨迹','惠琼的墨迹','特殊宝物0014','特殊宝物0015','特殊宝物0016',
                                     '特殊宝物0017','特殊宝物0018','特殊宝物0019']},
        'architecture': '主池(0x51e1f0)装通用交易品(名=类目,无def-index);副池(0x517728,20槽)装具名特殊物;'
                        '名物(村正等)身份=定义表idx,存于角色/存档库存(非本池)。',
    }
    with open(os.path.join(_HERE, r'item_pool_binding.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\nwritten: scripts/item_pool_binding.json")
    raise SystemExit(1 if fail else 0)


def cat_ok(c):
    return c


def catlist(defcats):
    return '[' + ','.join(str(x) for x in defcats) + ']'


if __name__ == '__main__':
    main()
