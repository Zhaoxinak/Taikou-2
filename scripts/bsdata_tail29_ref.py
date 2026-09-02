#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
续235 — BSDATA 主表尾部 5 字节 (stream 0x28..0x2c = entity +0x1c..+0x20) 统计特征化
========================================================================================

背景（续203 留口）：
  BSDATA 700×59B 明文主表，stream 偏移 0x28..0x2c 五字节 → 实体 +0x1c..+0x20，
  续203 已"特征化"但"须 emu/dump 坐死"精确玩法语义。本脚本用**本地明文 700 条主表**
  做纯静态数据统计，把五字节从"完全未知"推进到"结构化特征 + 已排除假设"。

方法：直接读 Taikou2 Original/BSDATA1.TR2（700×59B 明文，无加密），对每条记录取
  off 0x28/0x29/0x2a/0x2b/0x2c 字节，做分布/相关性分析。

关键发现（均可由本脚本自测复现）：
  [0x28] entity+0x1c：值 2..251，70.3% 恰为 32 的倍数（0x20/0x40/0x60/0x80/0xa0/0xc0 主导），
        余者为 base+小修正；与五维(统/武/内/交/魅)相关系数全 <0.16 → 非基础能力，
        为**累积/派生型等级**（技能総経験 或 统率派生等級类）。
  [0x29] entity+0x1d + [0x2a] entity+0x1e：**配对哨兵字段**，二者相关 0.85；
        二者默认同取 0xff（544/700=78%）；置位时 0x2a∈{0,1,2}、0x29 取关联值 →
        疑似「専門/特技」2 段码（高段 0x29 + 类别 0x2a）。
  [0x2b] entity+0x1f：0..62 小索引/计数，与各已知字段弱相关（|r|<0.10）。
  [0x2c] entity+0x20：0..100 评级；与 武力(0.43)/统率(0.36)/魅力(0.32) **松散正相关**，
        但 `0x2c ~ a*武力+b*统率` 线性回归 **R²=0.19**（加魅力仅 0.21）→
        **排除"战力=武力/统率 简单线性合成"假设**；为设计者给定或多输入评级，
        非确定性派生公式。

诚实边界：精确玩法语义（0x28 具体=哪种累积值、0x29/0x2a 专属特技码表、0x2b 索引指向）
  仍须 emu 或游戏文本交叉引用坐死 —— 本脚本提供的是**结构层证据**，非最终语义命名。

运行：`python scripts/bsdata_tail29_ref.py`  →  `RESULT: n/n checks passed`
"""
import os as _os
import struct
import math

_ROOT = _os.path.dirname(_os.path.abspath(__file__))
IMG = _ROOT + '/../Taikou2 Original/BSDATA1.TR2'
STRIDE = 59
OFFS = [0x28, 0x29, 0x2a, 0x2b, 0x2c]
KNOWN = {'统率': 0x16, '武力': 0x17, '内政': 0x18, '外交': 0x19, '魅力': 0x1a,
         '野心': 0x2f, '忠诚': 0x35, '生年': 0x27}


def _load():
    p = IMG
    if not _os.path.exists(p):
        p = _os.path.join(_ROOT, 'Taikou2 Original', 'BSDATA1.TR2')
    with open(_os.path.abspath(p), 'rb') as f:
        return f.read()


def _corr(a, b):
    n = len(a)
    ma = sum(a) / n
    mb = sum(b) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = math.sqrt(sum((x - ma) ** 2 for x in a))
    db = math.sqrt(sum((y - mb) ** 2 for y in b))
    return num / (da * db) if da and db else 0.0


def _run_tests():
    data = _load()
    N = len(data)
    n = N // STRIDE
    checks = passed = 0

    def chk(name, cond, extra=''):
        nonlocal checks, passed
        checks += 1
        if cond:
            passed += 1
        print("  [%s] %s%s" % ('OK' if cond else 'FAIL', name,
                               ('  ' + extra) if extra else ''))

    print("=== 续235 BSDATA 尾部 5 字节 统计特征化 (n=%d) ===\n" % n)
    chk("文件 700×59B 无缝平铺", N == 700 * STRIDE and N % STRIDE == 0)

    cols = {o: [data[r * STRIDE + o] for r in range(n)] for o in OFFS}
    knownv = {k: [data[r * STRIDE + o] for r in range(n)] for k, o in KNOWN.items()}

    # [0x28] 量化到 32
    v28 = cols[0x28]
    mult32 = sum(1 for v in v28 if v % 32 == 0)
    pct = 100.0 * mult32 / n
    chk("[0x28]entity+0x1c 70%%+ 为 32 倍数", pct >= 65.0,
        "(实测 %.1f%%, 范围 %d..%d)" % (pct, min(v28), max(v28)))
    corr28 = max(abs(_corr(v28, knownv[k])) for k in ('统率', '武力', '内政', '外交', '魅力'))
    chk("[0x28] 与五维零相关 (|r|<0.20)", corr28 < 0.20,
        "(max|r|=%.2f → 非基础能力)" % corr28)

    # [0x29] + [0x2a] 配对哨兵
    c292a = _corr(cols[0x29], cols[0x2a])
    chk("[0x29]entity+0x1d ↔ [0x2a]entity+0x1e 配对 (|r|>=0.80)", abs(c292a) >= 0.80,
        "(|r|=%.2f)" % abs(c292a))
    ff29 = sum(1 for v in cols[0x29] if v == 0xff)
    chk("[0x29] 默认哨兵 0xff 占多数", ff29 > n * 0.7,
        "(0xff=%d/%.0f=%.0f%%)" % (ff29, n, 100.0 * ff29 / n))
    a2 = set(cols[0x2a])
    chk("[0x2a]entity+0x1e 仅 {0xff,0,1,2}", a2.issubset({0xff, 0, 1, 2}),
        "(distinct=%s)" % sorted(a2))

    # [0x2b] 小索引
    v2b = cols[0x2b]
    chk("[0x2b]entity+0x1f 范围 0..62", min(v2b) >= 0 and max(v2b) <= 62,
        "(范围 %d..%d)" % (min(v2b), max(v2b)))

    # [0x2c] 0..100 评级，松散跟随战斗属性，但非简单线性合成
    v2c = cols[0x2c]
    chk("[0x2c]entity+0x20 范围 0..100", min(v2c) >= 0 and max(v2c) <= 100,
        "(范围 %d..%d)" % (min(v2c), max(v2c)))
    c武力 = _corr(v2c, knownv['武力'])
    c统率 = _corr(v2c, knownv['统率'])
    c魅力 = _corr(v2c, knownv['魅力'])
    chk("[0x2c] 松散跟随 武力/统率/魅力 (0.30<=r<=0.55)",
        0.30 <= c武力 <= 0.55 and 0.30 <= c统率 <= 0.55 and 0.30 <= c魅力 <= 0.55,
        "(武=%.2f 统=%.2f 魅=%.2f)" % (c武力, c统率, c魅力))
    # 线性回归 R² 排除简单合成
    import numpy as _np
    X = _np.array([[knownv['武力'][r], knownv['统率'][r], 1] for r in range(n)], float)
    Y = _np.array(v2c, float)
    beta = _np.linalg.lstsq(X, Y, rcond=None)[0]
    pred = X @ beta
    ss_res = float(((Y - pred) ** 2).sum())
    ss_tot = float(((Y - Y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot
    chk("[0x2c] 非 武力/统率 简单线性合成 (R²<0.30)", r2 < 0.30,
        "(R²=%.3f → 排除确定性派生)" % r2)

    print("\nRESULT: %d/%d checks passed" % (passed, checks))
    return passed == checks


if __name__ == "__main__":
    ok = _run_tests()
    raise SystemExit(0 if ok else 1)
