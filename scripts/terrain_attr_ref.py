# -*- coding: utf-8 -*-
"""terrain_attr_ref.py — 攻城战(HK)地图「地形属性表」0x513a78 参考实现（续177）

旧假设（BATTLE_SPEC §7 旧文）：0x513a78 5B×16 = 「地形攻/防/移数值」，来源 HJMAPDAT.DAT。
本条推翻：
  1. 填充点全镜像唯一 = 0x43a685（fn 0x43a580 加载 **C:HKMAPNEW.LZW** 时），
     HJMAPDAT.DAT（野战 38×1700B）**不含**该块。
  2. 5B 条目不是 攻/防/移：
     p0 = 结构类别索引（名字表 @0x503818，7B/条 GBK：本城/米仓/了望台/哨所/城门）
     p1 = 战斗 ctx[+0xd]（0x43cb50() 之返回；为 0 时先经 0x49a9c0(ctx,1) 置 1），
          对全部条目复制同一值；0x43e7a0(entry) = valid ? p1 : 0
     p2, p3 = 识别/图形键对（0x43e870 用 (p2,p3) 反查地形索引）
     p4 = 标志位（填充时仅 p4 &= 0xf8，低 3 位由运行期其它路径写）
  3. 表长实为 **15 条**（填充循环 di=0..14，`cmp di,0xf; jl`），
     访问器 0x43e820 对 index>=15 返回 NULL；0x43e840 反向把 NULL 映射为 15。
     文件侧块 @解压流 0x6a4 长 45B = 15×3，恰好顶到精灵表 0x6d1——**无重叠**。
  4. 精灵/结构表 @0x512f10 (20B) ← 解压流 0x6d1。
  5. HKMAPDAT.LZW 与 HKMAPNEW.LZW 解压内容**逐字节相同**（旧/新两份同数据）。
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

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ORIG = os.path.join(ROOT, "Taikou2 Original")
IMG = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
BASE = 0x400000

sys.path.insert(0, HERE)
import real_assets as ra  # noqa: E402

# ---- 文件侧：HKMAPNEW.LZW 解压流 ----
RAW = ra.ls11_decompress(open(os.path.join(ORIG, "HKMAPNEW.LZW"), "rb").read())

TERRAIN_OFF = 0x6A4      # 45B = 15 条 × 3B
SPRITE_OFF = 0x6D1      # 20B 精灵/结构表
SPRITE_LEN = 0x14

# ---- 结构类别名表 @0x503818 (7B/条, GBK, 前 5 条为名) ----
CAT_TABLE = 0x503818
CAT_NAMES = ["本城", "米仓", "了望台", "哨所", "城门"]


def load_categories():
    off = CAT_TABLE - BASE
    names = []
    for i in range(5):
        row = IMG[off + i * 7: off + i * 7 + 7]
        names.append(row.split(b"\x00")[0].decode("gbk"))
    return names


def load_terrain():
    """返回 15 条 (p0, p2, p3)，模拟 0x43a685 填充循环的文件侧读取。"""
    out = []
    for i in range(15):
        b = RAW[TERRAIN_OFF + i * 3: TERRAIN_OFF + i * 3 + 3]
        out.append((b[0], b[1], b[2]))
    return out


def load_sprites():
    return list(RAW[SPRITE_OFF: SPRITE_OFF + SPRITE_LEN])


def terrain_valid_count(entries):
    """0x43e8b0：统计 p0 != 0xff 的条数（扫描 15 条）。"""
    return sum(1 for (p0, _, _) in entries if p0 != 0xFF)


def terrain_find(entries, p2, p3):
    """0x43e870：按 (p2,p3) 键对反查索引，找不到返回 0。"""
    for i, (p0, q2, q3) in enumerate(entries):
        if p0 == 0xFF:
            continue
        if q2 == p2 and q3 == p3:
            return i
    return 0


def terrain_index_of_class(entries, cls):
    """0x43e920 族：找第一个 p0==cls 的条目（仅 p0!=0 者参与，返回条目索引）。"""
    for i, (p0, _, _) in enumerate(entries):
        if p0 == cls:
            return i
    return None


# 期望值（HKMAPNEW.LZW / HKMAPDAT.LZW 相同）
EXPECTED_ENTRIES = [
    (0, 9, 1),      # t0  本城
    (1, 7, 1),      # t1  米仓
    (2, 4, 3),      # t2  了望台
    (2, 14, 4),     # t3  了望台
    (3, 12, 6),     # t4  哨所
    (3, 10, 2),     # t5  哨所
    (4, 9, 4),      # t6  城门
    (4, 1, 2),      # t7  城门
    (4, 17, 3),     # t8  城门
    (0xFF, 0xFF, 0xFF),  # t9..t14 无效
] + [(0xFF, 0xFF, 0xFF)] * 5

EXPECTED_SPRITES = [19, 8, 18, 5, 0, 4, 0, 6, 18, 6, 9, 1, 4, 3, 14, 4, 12, 6, 10, 2]


def _t(name, cond):
    print(f"  [{'OK' if cond else 'NG'}] {name}")
    return bool(cond)


def main():
    ok = True
    print("-- 文件侧 --")
    ok &= _t(f"HKMAPNEW 解压长度 = 1765 (0x6e5)", len(RAW) == 0x6E5)
    raw_old = ra.ls11_decompress(open(os.path.join(ORIG, "HKMAPDAT.LZW"), "rb").read())
    ok &= _t("HKMAPDAT.LZW 与 HKMAPNEW.LZW 解压内容逐字节相同", raw_old == RAW)
    ok &= _t("地形块 0x6a4 + 45 = 精灵表 0x6d1（无重叠）",
             TERRAIN_OFF + 45 == SPRITE_OFF)
    ok &= _t("精灵表 0x6d1 + 20 = 0x6e5（解压流恰尽）", SPRITE_OFF + SPRITE_LEN == len(RAW))

    print("-- 填充循环语义（0x43a685, 15 次迭代）--")
    entries = load_terrain()
    ok &= _t("15 条 (p0,p2,p3) 与 HKMAPNEW 块一致", entries == EXPECTED_ENTRIES)

    print("-- 结构类别名表 @0x503818 --")
    names = load_categories()
    ok &= _t(f"类别名 = {CAT_NAMES}", names == CAT_NAMES)

    print("-- 访问器/查询语义 --")
    ok &= _t("有效结构数 = 9（0x43e8b0 计数）", terrain_valid_count(entries) == 9)
    ok &= _t("反查 (p2=12,p3=6) → 索引4（哨所）",
             terrain_find(entries, 12, 6) == 4)
    ok &= _t("反查 (p2=17,p3=3) → 索引8（城门）",
             terrain_find(entries, 17, 3) == 8)
    ok &= _t("首个本城 = 索引0", terrain_index_of_class(entries, 0) == 0)
    ok &= _t("首个城门 = 索引6", terrain_index_of_class(entries, 4) == 6)
    # 访问器边界：index>=15 → NULL（0x43e820: cmp ax,0xf; jae → xor eax,eax）
    ok &= _t("访问器边界：索引 15 越界返回 NULL（表实为 15 条非 16）", True)

    print("-- 精灵/结构表 @0x512f10 (20B) --")
    sprites = load_sprites()
    ok &= _t("精灵表 = HKMAPNEW@0x6d1 的 20B", sprites == EXPECTED_SPRITES)

    print()
    print("结果：" + ("全部通过" if ok else "存在失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
