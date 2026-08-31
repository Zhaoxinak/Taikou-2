# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
time_rollover_ref.py — 太阁立志传2 游戏日历 (月/日/年 进位) 参考实现 (self-test)
============================================================================
依据 (capstone 反汇编, 平坦映射 off = va - 0x400000):

[1] 日期推进主函数 0x4a0d50 (游戏时钟, 114 个 e8 调用方 = 主循环每帧; 下游 call 0x4a6ba0 AI)
    读取全局 (均为 1 字节):
        0x5205f1 = MONTH      (1..12)
        0x5205f2 = DAY        (1..30)
        0x5205f3 = TICK       (0..23, 日内计数, 24=1天)
        0x5205f0 = YEAR_OFF   (年 = 1560 + YEAR_OFF, 0..255)
    进位链 (0x4a0d50 内联):
        add TICK (esi = old_tick + [esp+0x20] delta)
        cmp si,0x18 (24); jb tail            ; TICK<24 -> 不进日, 仅写 TICK
        idiv 0x18 -> TICK = TICK % 24        ; 进日, 余数回填
        inc DAY
        cmp bp,0x1f (31); jb store_day       ; DAY<31 -> 存日, 不进月
        inc MONTH ; DAY=1
        cmp bx,0xd (13); jb store_month      ; MONTH<13 -> 存月, 不进年
        inc YEAR ; MONTH=1                    ; 进年, 月归 1
    => 日进位阈值 31 (即每月 30 天); 月进位阈值 13 (即每年 12 月); 无闰年分支。

[2] 四个 setter (this 指针 ecx = 0x5205f0, 寄存器间接写 -> 全镜像写指令扫描 0 命中):
    0x49a120 setYear (ecx+0):
        eax = (arg - 0x618) & 0xffff ; cmp eax,0xff ; jbe ok ; mov eax,0xff ; write byte[ecx+0]
        => YEAR_OFF 上限 255 => 年最大值 1560 + 255 = 1815 (年阈值 1815 = 字节宽度上限)
    0x49a140 setMonth(ecx+1):
        eax = arg & 0xffff ; cmp eax,0xc(12) ; jbe ok ; mov eax,0xc ; and ; cmp 1 ; jae ok ; mov eax,1 ; write byte[ecx+1]
        => MONTH 夹紧 [1,12]
    0x49a170 setDay  (ecx+2):
        eax = arg & 0xffff ; cmp eax,0x1e(30) ; jbe ok ; mov eax,0x1e ; and ; cmp 1 ; jae ok ; mov eax,1 ; write byte[ecx+2]
        => DAY 夹紧 [1,30]
    0x49a1a0 setTick (ecx+3):
        eax = arg & 0xffff ; cmp eax,0x17(23) ; jbe ok ; mov eax,0x17 ; write byte[ecx+3]
        => TICK 夹紧 [0,23]

结论: 所有月份均为 30 天, 每年 12 个月, 无闰年 (无 days_in_month 表, 无闰年分支)。
      月进位上限 12 / 日进位上限 30 由 setter clamp 与内联 cmp 双重保证。
      日期只经 ecx=0x5205f0 的 this 指针 setter 写入 —— 这正解释了 续116「全镜像写指令扫描 0 命中」的墙。
"""

# ---------- 反汇编实证常量 ----------
YEAR_BASE      = 0x618     # 1560, 0x49a120 中 add eax,0xfffff9e8 (= -0x618)
YEAR_OFF_MAX   = 0xff      # 255, 0x49a120 中 cmp eax,0xff
MONTH_MAX      = 0xc       # 12,  0x49a140 中 cmp eax,0xc
MONTH_MIN      = 1
DAY_MAX        = 0x1e      # 30,  0x49a170 中 cmp eax,0x1e
DAY_MIN        = 1
TICK_MAX       = 0x17      # 23,  0x49a1a0 中 cmp eax,0x17
TICKS_PER_DAY  = 0x18      # 24,  0x4a0d50 中 cmp si,0x18 / idiv 0x18
DAY_CARRY      = 0x1f      # 31,  0x4a0d50 中 cmp bp,0x1f  (日进位阈值)
MONTH_CARRY    = 0xd       # 13,  0x4a0d50 中 cmp bx,0xd   (月进位阈值)
YEAR_MAX       = YEAR_BASE + YEAR_OFF_MAX   # 1815


# ---------- setter (复刻 0x49a120/0x49a140/0x49a170/0x49a1a0) ----------
def set_year(year: int) -> int:
    """0x49a120: 写 byte[0x5205f0] = (year-1560) 夹紧 [0,255]"""
    off = (year - YEAR_BASE) & 0xffff
    if off > YEAR_OFF_MAX:
        off = YEAR_OFF_MAX
    return off

def set_month(m: int) -> int:
    """0x49a140: 写 byte[0x5205f1] = clamp(m, 1, 12)"""
    if m > MONTH_MAX:
        m = MONTH_MAX
    if m < MONTH_MIN:
        m = MONTH_MIN
    return m

def set_day(d: int) -> int:
    """0x49a170: 写 byte[0x5205f2] = clamp(d, 1, 30)"""
    if d > DAY_MAX:
        d = DAY_MAX
    if d < DAY_MIN:
        d = DAY_MIN
    return d

def set_tick(t: int) -> int:
    """0x49a1a0: 写 byte[0x5205f3] = clamp(t, 0, 23)"""
    if t > TICK_MAX:
        t = TICK_MAX
    return t


def advance(tick: int, day: int, month: int, year_off: int, delta: int):
    """
    复刻 0x4a0d50 单次调用 (delta = 传入的 [esp+0x20] 计时增量, 实机每帧=1)。
    返回新 (tick, day, month, year_off)。
    注: 每帧最多进 1 日 (与反汇编一致: TICK>=24 时只 inc DAY 一次)。
    """
    tick = set_tick(tick)  # 进入前已是合法值
    year = YEAR_BASE + year_off
    tick += delta
    if tick >= TICKS_PER_DAY:
        tick = tick % TICKS_PER_DAY
        day += 1
        if day == DAY_CARRY:           # 31 -> 进月
            month += 1
            day = 1
            if month == MONTH_CARRY:   # 13 -> 进年, 月归 1
                year += 1
                month = 1
    # 经 setter 夹紧写回 (0x49a120/0x49a140/0x49a170/0x49a1a0)
    year_off = set_year(year)
    month = set_month(month)
    day = set_day(day)
    tick = set_tick(tick)
    return tick, day, month, year_off


def _run_tests():
    ok = 0
    total = 0

    def check(name, got, exp):
        nonlocal ok, total
        total += 1
        if got == exp:
            ok += 1
        else:
            print(f"  FAIL: {name}: got={got!r} exp={exp!r}")

    # --- 常量实证 (与反汇编字节一一对应) ---
    check("YEAR_BASE=1560", YEAR_BASE, 1560)
    check("YEAR_OFF_MAX=255", YEAR_OFF_MAX, 255)
    check("MONTH_MAX=12", MONTH_MAX, 12)
    check("DAY_MAX=30", DAY_MAX, 30)
    check("TICK_MAX=23", TICK_MAX, 23)
    check("TICKS_PER_DAY=24", TICKS_PER_DAY, 24)
    check("DAY_CARRY=31", DAY_CARRY, 31)
    check("MONTH_CARRY=13", MONTH_CARRY, 13)
    check("YEAR_MAX=1815", YEAR_MAX, 1815)

    # --- setter 夹紧 ---
    check("setYear(1560)->0", set_year(1560), 0)
    check("setYear(1815)->255", set_year(1815), 255)
    check("setYear(2000) clamp->255", set_year(2000), 255)
    check("setYear(1000) -> clamp0(neg wrap)", set_year(1000), (1000 - 1560) & 0xffff if (1000 - 1560) & 0xffff <= 255 else 255)
    check("setMonth(1)->1", set_month(1), 1)
    check("setMonth(12)->12", set_month(12), 12)
    check("setMonth(13)->12", set_month(13), 12)
    check("setMonth(0)->1", set_month(0), 1)
    check("setMonth(99)->12", set_month(99), 12)
    check("setDay(1)->1", set_day(1), 1)
    check("setDay(30)->30", set_day(30), 30)
    check("setDay(31)->30", set_day(31), 30)
    check("setDay(0)->1", set_day(0), 1)
    check("setDay(99)->30", set_day(99), 30)
    check("setTick(0)->0", set_tick(0), 0)
    check("setTick(23)->23", set_tick(23), 23)
    check("setTick(24)->23", set_tick(24), 23)
    check("setTick(99)->23", set_tick(99), 23)

    # --- 单次进位: 月末 ---
    # 1560-01-30 + 1 tick (24) -> 02-01
    t, d, m, y = advance(0, 30, 1, 0, 24)
    check("end-of-month: day30+m1tick -> m2d1", (t, d, m, y), (0, 1, 2, 0))
    # 月末不足 24 tick 不进日
    t, d, m, y = advance(0, 30, 1, 0, 23)
    check("end-of-month: +23tick no rollover", (t, d, m, y), (23, 30, 1, 0))

    # --- 单次进位: 年末 (12月30日) ---
    t, d, m, y = advance(0, 30, 12, 0, 24)
    check("end-of-year: 12-30+1tick -> 1561-01-01", (t, d, m, y), (0, 1, 1, 1))

    # --- 无闰年: 2 月也是 30 天 ---
    # 02-01 + 29 次 advance(24) 应到 02-30, 再 +1 -> 03-01
    t, d, m, y = 1, 1, 2, 0
    for _ in range(29):
        t, d, m, y = advance(t, d, m, y, 24)
    check("feb has 30 days (reaches 02-30)", (d, m, y), (30, 2, 0))
    t, d, m, y = advance(t, d, m, y, 24)
    check("feb 30 -> mar 1 (no 28/29)", (d, m, y), (1, 3, 0))

    # --- 全年模拟: 360 次 advance(24) = 12 月 * 30 天, 回到 1561-01-01 ---
    t, d, m, y = 0, 1, 1, 0
    max_day_seen, max_month_seen = 0, 0
    for _ in range(360):
        t, d, m, y = advance(t, d, m, y, 24)
        max_day_seen = max(max_day_seen, d)
        max_month_seen = max(max_month_seen, m)
        # 不变量: 日<=30, 月<=12 (全月 30 天 / 全年 12 月)
        if d > 30 or m > 12:
            check("invariant day<=30 month<=12", False, True)
    check("1 year sim -> 1561-01-01", (t, d, m, y), (0, 1, 1, 1))
    check("invariant: max day seen <=30 (no 31-day month)", max_day_seen, 30)
    check("invariant: max month seen <=12", max_month_seen, 12)

    # --- 年阈值 1815: 到达后 clamp 不再增长 ---
    # YEAR_OFF=255 (年 1815) + 1 天 -> 仍 255 (字节宽度上限)
    t, d, m, y = advance(0, 30, 12, 255, 24)   # 1815-12-30 +1 -> 跨年
    check("year cap 1815: off stays 255", y, 255)
    check("year cap: month resets to 1 on carry", m, 1)
    check("year cap: day resets to 1 on carry", d, 1)

    # --- 字节宽度: YEAR_OFF 为单字节, 不可能 >255 ---
    check("YEAR_OFF is byte (<=255)", YEAR_OFF_MAX <= 255, True)

    print(f"\nRESULT: {ok}/{total} checks passed")
    return ok, total


if __name__ == "__main__":
    ok, total = _run_tests()
    import sys
    sys.exit(0 if ok == total else 1)
