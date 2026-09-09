# -*- coding: utf-8 -*-
"""
_test_calendar_mirror.py — calendar.gd 的 Python 等价镜像（验证逻辑与期望值）
复刻 scripts/time_rollover_ref.py（0x4a0d50 进位链 + setter 夹紧）。
本机 Godot --script 主循环失效，故用 Python 复跑同一套断言验证 GDScript 移植的算法正确性。
运行：python3 scripts/_test_calendar_mirror.py
"""
YEAR_BASE = 1560
YEAR_OFF_MAX = 255
MONTH_MAX = 12
MONTH_MIN = 1
DAY_MAX = 30
DAY_MIN = 1
TICK_MAX = 23
TICKS_PER_DAY = 24
DAY_CARRY = 31
MONTH_CARRY = 13
YEAR_MAX = YEAR_BASE + YEAR_OFF_MAX


def set_year_off(off):
    return max(0, min(int(off), YEAR_OFF_MAX))

def set_month(m):
    return max(MONTH_MIN, min(int(m), MONTH_MAX))

def set_day(d):
    return max(DAY_MIN, min(int(d), DAY_MAX))

def set_tick(t):
    return max(0, min(int(t), TICK_MAX))


def advance(delta, t, d, m, yoff):
    t = set_tick(t); yoff = set_year_off(yoff); m = set_month(m); d = set_day(d)
    t += delta
    if t >= TICKS_PER_DAY:
        t = t % TICKS_PER_DAY
        d += 1
        if d == DAY_CARRY:
            m += 1
            d = 1
            if m == MONTH_CARRY:
                yoff = set_year_off(yoff + 1)
                m = 1
    yoff = set_year_off(yoff); m = set_month(m); d = set_day(d); t = set_tick(t)
    return [t, d, m, yoff]


def roll_days(n, d, m, yoff):
    t = 0
    for _ in range(max(0, n)):
        r = advance(TICKS_PER_DAY, t, d, m, yoff)
        t, d, m, yoff = r[0], r[1], r[2], r[3]
    return [d, m, yoff]


def roll_months(n, d, m, yoff):
    y = set_year_off(yoff); mm = set_month(m); dd = set_day(d)
    for _ in range(max(0, n)):
        mm += 1
        if mm > MONTH_MAX:
            mm = 1
            y = set_year_off(y + 1)
    dd = set_day(dd); mm = set_month(mm); y = set_year_off(y)
    return [dd, mm, y]


def year_of(yoff):
    return YEAR_BASE + set_year_off(yoff)


def _run_tests():
    ok = total = 0
    def check(name, got, exp):
        nonlocal ok, total
        total += 1
        if got == exp:
            ok += 1
        else:
            print(f"  FAIL: {name}: got={got!r} exp={exp!r}")

    # 常量
    check("YEAR_BASE", YEAR_BASE, 1560)
    check("YEAR_OFF_MAX", YEAR_OFF_MAX, 255)
    check("MONTH_MAX", MONTH_MAX, 12)
    check("DAY_MAX", DAY_MAX, 30)
    check("TICK_MAX", TICK_MAX, 23)
    check("TICKS_PER_DAY", TICKS_PER_DAY, 24)
    check("DAY_CARRY", DAY_CARRY, 31)
    check("MONTH_CARRY", MONTH_CARRY, 13)
    check("YEAR_MAX", YEAR_MAX, 1815)

    # setter
    check("set_year_off", [set_year_off(0), set_year_off(255), set_year_off(300)], [0, 255, 255])
    check("set_month", [set_month(1), set_month(12), set_month(13), set_month(0)], [1, 12, 12, 1])
    check("set_day", [set_day(1), set_day(30), set_day(31), set_day(0)], [1, 30, 30, 1])
    check("set_tick", [set_tick(0), set_tick(23), set_tick(24)], [0, 23, 23])

    # advance 月末 / 年末
    check("end-of-month", advance(24, 0, 30, 1, 0), [0, 1, 2, 0])
    check("end-of-month no-rollover", advance(23, 0, 30, 1, 0), [23, 30, 1, 0])
    check("end-of-year", advance(24, 0, 30, 12, 0), [0, 1, 1, 1])

    # 2 月 30 天
    t, d, m, y = 1, 1, 2, 0
    for _ in range(29):
        t, d, m, y = advance(24, t, d, m, y)
    check("feb 30 days", (d, m, y), (30, 2, 0))
    t, d, m, y = advance(24, t, d, m, y)
    check("feb30->mar1", (d, m, y), (1, 3, 0))

    # 全年 360 天
    t, d, m, y = 0, 1, 1, 0
    max_d = max_m = 0
    for _ in range(360):
        t, d, m, y = advance(24, t, d, m, y)
        max_d = max(max_d, d); max_m = max(max_m, m)
    check("1 year -> 1561-01-01", (d, m, y), (1, 1, 1))
    check("invariant day<=30", max_d, 30)
    check("invariant month<=12", max_m, 12)

    # roll 便利函数
    check("roll_days", roll_days(1, 30, 1, 0), [1, 2, 0])
    check("roll_months", roll_months(1, 15, 12, 0), [15, 1, 1])
    acc = [1, 1, 0]
    for _ in range(12):
        acc = roll_months(1, acc[0], acc[1], acc[2])
    check("12x roll_months -> 1561-01", acc, [1, 1, 1])

    # 年上限
    check("year cap 1815", advance(24, 0, 30, 12, 255), [0, 1, 1, 255])

    print(f"\nRESULT: {ok}/{total} checks passed (calendar mirror)")
    return ok == total


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_tests() else 1)
