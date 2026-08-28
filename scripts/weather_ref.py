#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
太阁立志传2 · 天气/季节系统 参考实现（1:1 复刻 TAIK2W95.exe 逻辑）

来源：脱壳映像 scripts/_unpacked_mem.bin（基址 0x400000）逐指令反汇编。

原版函数对应
------------
0x43cad0  getWeather()          -> word[0x513530]
0x43cae0  setWeather(w)         -> word[0x513530] = w
0x43caf0  weatherBucket()       -> 0 if w==0 else (2 if w>2 else 1)   （3 档：晴/雨系/雪）
0x43cb10  getWetFlag()          -> dword[0x51352c]      （降水/湿润标志）
0x43cb20  setWetFlag(v)         -> dword[0x51352c] = v
0x43ca60  getDayCounter()       -> byte[0x513540]
0x43cfc0  weather_tick_simple() 简版（无地域），调用点 0x4347b6（counter%4==0 时）
0x43d0e0  weather_tick_region() 完整版（含地域气候），调用点 0x434e6c
0x43d060  weather_transition(threshold, mode)

概率表（全部静态、单位=百分比，语义 = 「天气保持不变」的概率）
---------------------------------------------------------------
0x5037b8  T_SIMPLE   [season*3 + weather]     简版用
0x5037c5  T_SEASON   [season*3 + weather]     完整版·非冬季用（base 有 3 字节前导 0）
0x5037d4  T_WINTER_SNOWREG [weather]          完整版·冬季·雪国用
0x5037d8  T_WINTER_NORMAL  [weather]          完整版·冬季·非雪国用

天气状态编码 word[0x513530]
---------------------------
0 = 晴   1 = 曇(阴)   2 = 雨   3 = 雪

季节 = (月 // 3) & 3     ⇒ 0=冬{12,1,2}  1=春{3,4,5}  2=夏{6,7,8}  3=秋{9,10,11}
月份来源：byte[0x5205f1]

地域气候：当前所在国 id = word[0x524866]（<49）
          国情记录 = 0x519548 + id*5，byte[+1] = 地域/气候组
          气候组 ∈ {0, 2, 4} ⇒ 雪国（冬季走 SNOWREG 分支、允许 雨→雪）

战斗联动：0x42d62e 读 getWetFlag()，非零且单位兵种类别 kind==2（铁炮/洋枪）
          时战力 ×2/3（0x42d643 `shl eax,1; imul 0x55555556`）
"""

import os, struct, random, collections

BASE = 0x400000
_HERE = os.path.dirname(os.path.abspath(__file__))
_IMG = os.path.join(_HERE, "_unpacked_mem.bin")

# ---------------------------------------------------------------- 静态表
# 0x5037b8 .. 0x5037c3（12B，season*3 + weather，weather 只到 2）
T_SIMPLE = [90, 80, 40,   # 冬: 晴 曇 雨
            80, 60, 70,   # 春
            90, 20, 50,   # 夏
            80, 60, 90]   # 秋

# 0x5037c5 起 15B。索引 = season*3 + weather，season 只取 1..3，weather 0..3
# 注意：stride 是 3 而列有 4（weather==3 会 alias 到下一行首列）——原版如此，不是笔误
T_SEASON = [0, 0, 0,
            70, 60, 50,   # 春: 晴 曇 雨   (weather3 → alias 80)
            80, 20, 60,   # 夏           (weather3 → alias 60)
            60, 50, 70,   # 秋           (weather3 → alias 0)
            0, 0, 0]

T_WINTER_SNOWREG = [20, 50, 0]    # 0x5037d4  冬·雪国  晴/曇/雨 保持率
T_WINTER_NORMAL  = [90, 40, 20]   # 0x5037d8  冬·非雪国 晴/曇/雨 保持率

CLEAR, CLOUDY, RAIN, SNOW = 0, 1, 2, 3
WEATHER_NAME = {0: "晴", 1: "曇", 2: "雨", 3: "雪"}
SEASON_NAME = {0: "冬", 1: "春", 2: "夏", 3: "秋"}
SNOW_CLIMATE_GROUPS = (0, 2, 4)


def season_of(month: int) -> int:
    """0x43cfe9 / 0x43d0f9: eax = abs(month//3) & 3，再按符号还原（月为正 ⇒ 等价下式）"""
    return (month // 3) & 3


# ---------------------------------------------------------------- 状态机
class Weather:
    """一份天气运行时状态。rnd(n) 需返回 [0,n) 均匀整数（原版 = 0x4ebd60 rand()%n）。"""

    def __init__(self, weather=CLEAR, wet=0, rnd=None):
        self.w = weather          # word[0x513530]
        self.wet = wet            # dword[0x51352c]
        self._rnd = rnd or (lambda n: random.randrange(n))

    # 0x43caf0
    def bucket(self) -> int:
        if self.w == 0:
            return 0
        return 2 if self.w > 2 else 1

    # 0x43d060  weather_transition(threshold, mode) -> 新天气 或 None(不变)
    def _transition(self, threshold: int, mode: int, r1: int):
        if r1 < threshold:
            return None                      # 0x43d074: or ax,0xffff → -1 = 不变
        cur = self.w
        if cur == 0:                         # 0x43d084
            return CLOUDY
        if cur == 1:                         # 0x43d08b
            if mode == 2:                    # 0x43d091 雪国冬季：曇 90% 直接转雪
                return CLEAR if self._rnd(100) < 10 else SNOW
            return CLEAR if (r1 & 1) else RAIN   # 0x43d0b0 奇→晴 偶→雨
        # cur >= 2                           # 0x43d0ce
        return SNOW if mode != 0 else CLOUDY

    # --------------------------------------------------- 0x43cfc0 简版
    def tick_simple(self, month: int):
        r1 = self._rnd(100)
        if self.w == SNOW:                   # 0x43cfd4
            if r1 < 20:                      # 0x43cfda cmp si,0x14
                self.wet ^= 1                # 0x43cfe0 xor dword[0x51352c],1
            return
        s = season_of(month)
        thr = T_SIMPLE[s * 3 + self.w]       # 0x43d019
        new = self._transition(thr, 0, r1)
        if new is None:
            return
        self.wet = 1 if new == RAIN else 0   # 0x43d034 sete dl / call 0x43cb20
        self.w = new

    # --------------------------------------------------- 0x43d0e0 完整版
    def tick_region(self, month: int, climate_group: int):
        """climate_group = byte[0x519548 + province*5 + 1]；province>=49 时原版传 0"""
        r1 = self._rnd(100)
        s = season_of(month)

        if s != 0:                                    # 0x43d146 非冬季
            thr = T_SEASON[s * 3 + self.w]            # 0x43d248
            new = self._transition(thr, 0, r1)
            if new is None:
                return
            self.wet = 1 if new == RAIN else 0        # 0x43d265
            self.w = new
            return

        snow_region = climate_group in SNOW_CLIMATE_GROUPS   # 0x43d14f/0x43d154/0x43d15a

        if self.w == SNOW:
            if snow_region:                           # 0x43d1c5
                thr = 80 if self.wet else 60
                cut = 70                              # 0x43d1f5 cmp bx,0x46
            else:                                     # 0x43d166
                thr = 20 if self.wet else 40
                cut = 80                              # 0x43d199 cmp bx,0x50
            if r1 < thr:
                return                                # 保持
            if self.wet:
                self.wet = 0                          # edi = flag^1
                self.w = SNOW
            elif r1 >= cut:
                self.wet = 1
                self.w = SNOW
            else:
                self.wet = 0
                self.w = CLEAR
            return

        if snow_region:                               # 0x43d201
            mode, thr = 2, T_WINTER_SNOWREG[self.w]
        else:                                         # 0x43d1ac
            mode, thr = 1, T_WINTER_NORMAL[self.w]
        new = self._transition(thr, mode, r1)
        if new is None:
            return
        self.wet = 1 if new in (RAIN, SNOW) else 0    # 0x43d223/0x43d233
        self.w = new


# ---------------------------------------------------------------- 战斗联动
def gun_strength_penalty(strength: int, wet_flag: int, kind: int) -> int:
    """0x42d62e：降水中且 kind==2（铁炮/洋枪）⇒ 战力 ×2/3"""
    if wet_flag and kind == 2:
        return (strength * 2) // 3
    return strength


# ---------------------------------------------------------------- 自校验
def verify_against_image():
    if not os.path.exists(_IMG):
        print("[skip] 未找到 %s，跳过映像自校验" % _IMG)
        return None
    mem = open(_IMG, "rb").read()
    rd = lambda va, n: list(mem[va - BASE: va - BASE + n])
    ok = True
    checks = [
        ("T_SIMPLE          @0x5037b8", rd(0x5037B8, 12), T_SIMPLE),
        ("T_SEASON          @0x5037c5", rd(0x5037C5, 15), T_SEASON),
        ("T_WINTER_SNOWREG  @0x5037d4", rd(0x5037D4, 3), T_WINTER_SNOWREG),
        ("T_WINTER_NORMAL   @0x5037d8", rd(0x5037D8, 3), T_WINTER_NORMAL),
    ]
    for name, got, want in checks:
        good = got == want
        ok &= good
        print(("  [OK] " if good else "  [NG] ") + name + "  " + str(got))
    return ok


def _sanity_montecarlo():
    """跑 20 年，验证四季/雪国分布符合表意（雪只在冬季出现；雪国冬季雪占比远高）"""
    print("\n--- Monte-Carlo（完整版 tick_region，每月 4 tick）---")
    for label, climate in (("雪国(group=0)", 0), ("非雪国(group=1)", 1)):
        stat = collections.defaultdict(collections.Counter)
        wx = Weather(rnd=lambda n: random.randrange(n))
        for year in range(20):
            for month in range(1, 13):
                for _ in range(4):
                    wx.tick_region(month, climate)
                    stat[season_of(month)][wx.w] += 1
        print(" %s" % label)
        for s in (0, 1, 2, 3):
            tot = sum(stat[s].values())
            line = "  ".join("%s%5.1f%%" % (WEATHER_NAME[w], 100.0 * stat[s][w] / tot)
                             for w in (0, 1, 2, 3))
            print("   %s  %s" % (SEASON_NAME[s], line))


if __name__ == "__main__":
    random.seed(20260827)
    print("=== 天气表 · 映像自校验 ===")
    r = verify_against_image()
    print("  => %s" % ("全部一致" if r else ("不一致！" if r is False else "已跳过")))

    print("\n=== 简版 tick_simple 轨迹（2 月，30 tick）===")
    wx = Weather(rnd=lambda n: random.randrange(n))
    trace = []
    for _ in range(30):
        wx.tick_simple(2)
        trace.append(WEATHER_NAME[wx.w] + ("*" if wx.wet else ""))
    print("  " + " ".join(trace))

    _sanity_montecarlo()

    print("\n=== 铁炮雨雪惩罚 ===")
    for wet in (0, 1):
        print("  wet=%d  kind2 战力 300 -> %d" % (wet, gun_strength_penalty(300, wet, 2)))
