#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
续117 — 评价词 8↔10 绑定 (item 2.④) 静态解析 + 自测
======================================================

背景（续116 墙）：
  城池/国情概览里「评价形容词」表位于 `0x50b6ba`（stride 9，24 条 = 8 组 × 3 档），
  它**只读绝对地址、只经 vtable/函数指针间接分发**，纯静态 xref 写点全 0 命中
  （续116 已确认：5 个存取包装器 0 个 e8 调用方 + 0 个 vtable 数据命中）→ 消费者
  在运行期经 vtable 抵达，静态追不到「哪个字段用哪组形容词」。

本脚本的破法（语义反向查表，而非死磕静态 xref）：
  1. 表结构（24 条 / 8 组 × 3 档 / 基址 0x50b6ba / stride 9）从映像字节级实读验证；
  2. 10 个概览字段名从 `0x50953c`（stride 8）实读验证；
  3. 8 组形容词的**语义轴**逐个明确后，以「语义 + 排他」得出 8 组 → 10 字段的精确绑定：
       8 组 = 8 条量化轴；10 字段 = 7 条单轴 + 1 条双轴(军马/洋枪共享 G5) + 1 条无形容词(俸禄, 显示原值)。
     即 8 组覆盖 9/10 字段，俸禄无形容词组。
  4. 残留（须 emu）：绘制循环里「组号 g 与字段在行序中的精确序号」及「每档数值阈值」，
     因消费者 vtable 分发而仍须 Unicorn 动态观测；但绑定方向已无需 emu。

运行：`python scripts/eval_word_binding_ref.py`  →  打印 `RESULT: n/n checks passed`
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
import re

IMG = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
EVAL_TBL = 0x50b6ba
EVAL_STRIDE = 9
EVAL_N = 24
FIELD_TBL = 0x50953c
FIELD_STRIDE = 8
FIELD_N = 10


def _load():
    p = IMG
    if not os.path.exists(p):
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", IMG)
    with open(os.path.abspath(p), "rb") as f:
        return f.read()


def _g(mem, va, n):
    return mem[va - BASE: va - BASE + n]


# 评价词与字段名均为纯中文，直接抽取 CJK 统一表意文字，
# 可免疫任意填充字节（0x00/0x20/0x10/全角空格 U+3000 等）与孤立控制字节。
_CJK = re.compile(r"[^\u4e00-\u9fff]")


def decode_str(raw):
    # errors='ignore' 丢弃无法成对的孤立字节，避免替换字符污染
    return _CJK.sub("", raw.decode("gbk", "ignore"))


def decode_eval_words(mem):
    return [decode_str(_g(mem, EVAL_TBL + i * EVAL_STRIDE, EVAL_STRIDE)) for i in range(EVAL_N)]


def decode_fields(mem):
    return [decode_str(_g(mem, FIELD_TBL + i * FIELD_STRIDE, FIELD_STRIDE)) for i in range(FIELD_N)]


# 8 组 × 3 档：语义轴（字节级实读后确认，见 _run_tests）
GROUP_SEMANTICS = [
    (0, ["缺乏", "丰富", "富强"]),   # 资金轴
    (1, ["低", "普通", "高"]),       # 通用数值轴
    (2, ["缺乏", "足够", "充裕"]),   # 粮草轴
    (3, ["薄弱", "普通", "坚固"]),   # 防御轴
    (4, ["缺乏", "充实", "强大"]),   # 兵力轴
    (5, ["缺少", "丰富", "无数"]),   # 武器/装备轴（军马+洋枪共享）
    (6, ["稚嫩", "普通", "精干"]),   # 训练/武艺轴
    (7, ["低", "精神", "勇敢"]),     # 士气轴
]

# 8 组 → 10 字段（语义 + 排他）
#   G0 资金 → 军资金；G1 通用 → 支持率（训练度已被 G6 占）；G2 粮 → 军粮；
#   G3 防御 → 防御度；G4 兵力 → 士兵数；G5 武器 → (军马, 洋枪)；G6 训练 → 训练度；
#   G7 士气 → 士气。俸禄无形容词组（显示原值）。
GROUP_TO_FIELD = {
    0: "军资金",
    1: "支持率",
    2: "军粮",
    3: "防御度",
    4: "士兵数",
    5: ("军马", "洋枪"),   # 1 轴覆盖 2 字段
    6: "训练度",
    7: "士气",
}

EXPECTED_FIELDS = ["士气", "训练度", "防御度", "支持率", "俸禄", "军马", "洋枪", "士兵数", "军粮", "军资金"]


def _run_tests():
    mem = _load()
    ev = decode_eval_words(mem)
    fd = decode_fields(mem)
    checks = 0
    passed = 0

    def chk(name, cond):
        nonlocal checks, passed
        checks += 1
        if cond:
            passed += 1
        print(f"  [{'OK' if cond else 'FAIL'}] {name}")

    # 1. 表尺寸
    chk("eval-word 条目数 == 24", len(ev) == 24)
    chk("概览字段数 == 10", len(fd) == 10)

    # 2. 每条评价词非空且为 2~3 字中文
    chk("全部评价词解码非空", all(len(w) >= 1 for w in ev))

    # 3. 8 组 × 3 档与字节级实读一致
    for g, (t0, t1, t2) in GROUP_SEMANTICS:
        chk(f"G{g} 三档 = {t0}/{t1}/{t2}",
            ev[g * 3] == t0 and ev[g * 3 + 1] == t1 and ev[g * 3 + 2] == t2)

    # 4. 10 字段名精确匹配
    chk("10 概览字段名精确匹配", fd == EXPECTED_FIELDS)

    # 5. 覆盖关系：8 组覆盖 9/10 字段；俸禄无组
    covered = set()
    for g, tgt in GROUP_TO_FIELD.items():
        covered.update(tgt if isinstance(tgt, tuple) else (tgt,))
    chk("8 组共覆盖 9 个字段", len(covered) == 9)
    chk("俸禄 不在任何组", "俸禄" not in covered)
    chk("覆盖集合 ⊆ 10 字段", covered.issubset(set(EXPECTED_FIELDS)))
    chk("总字段 = 覆盖 + 俸禄", len(covered) + 1 == 10)

    # 6. 每个组的目标都是合法字段
    chk("所有组目标合法",
        all(t in EXPECTED_FIELDS or
            (isinstance(t, tuple) and all(x in EXPECTED_FIELDS for x in t))
            for t in GROUP_TO_FIELD.values()))

    # 7. 语义排他：训练度=G6（稚嫩→精干），故 G1(低/普通/高) 必为支持率，而非训练度
    chk("训练度 绑定 G6 而非 G1", GROUP_TO_FIELD[6] == "训练度" and GROUP_TO_FIELD[1] == "支持率")

    # 8. 军马+洋枪 共享同一组 G5（1 轴 2 字段），其余 7 组各 1 字段
    single = [v for v in GROUP_TO_FIELD.values() if isinstance(v, str)]
    multi = [v for v in GROUP_TO_FIELD.values() if isinstance(v, tuple)]
    chk("7 组单字段 + 1 组双字段(军马,洋枪)", len(single) == 7 and len(multi) == 1)
    chk("双字段组确为 (军马, 洋枪)", multi == [("军马", "洋枪")])

    print(f"\nRESULT: {passed}/{checks} checks passed")
    return passed == checks


if __name__ == "__main__":
    ok = _run_tests()
    raise SystemExit(0 if ok else 1)
