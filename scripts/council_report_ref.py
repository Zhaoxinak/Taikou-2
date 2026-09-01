# -*- coding: utf-8 -*-
"""
council_report_ref.py — 太阁2 評定「报告 handler 选取策略」可执行参考实现
对应 EXE 0x460420（ID -> 13 报告中某一个 handler 索引）。

闭环 0x460420 的反汇编，依赖项全部已定位：
  - di      = word[0x516610]              (0x49f6b0 返回该全局，= 当前選択ID)
  - count   = word[0x513fcc]              (总报告条目数)
  - asked   = 0x460500() = #{i : 0x513fd4[i] & 0x8000}   (已询问数)
  - slots   = word[0x513fe0 + i*2] (i=0..12)  (非零=该报告类型当前可展示)
  - flag6   = word[0x513ff6]  (= slots[11], 馬販子 handler 11 可用性)
  - flag8   = word[0x513ff8]  (= slots[12], 米価 handler 12 可用性)
  - prob(p) = 0x4ebe40(p) = (rand()%100) < p
  - rand_avail() = 0x460530 = 随机挑一个 slots[i]!=0 的 i (0..12)

返回 handler 索引 0..12 后，调用方会执行 word[0x513fe0 + idx*2] = 0（标记该槽已用）。
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

import random

HANDLER_COUNT = 13          # 0x504898 表项数
SLOT_TABLE    = 0x513fe0    # 13 个报告槽（word[i*2]）
ASKED_TABLE   = 0x513fd4    # 菜单条目表（word[i*2]，bit15=已询问）
ENTRY_COUNT   = 0x513fcc    # word 总条目数
SEL_ID        = 0x516610    # word 当前選択ID（0x49f6b0 指向此处）


def prob_check(p, rng):
    """0x4ebe40(p): 返回 1 当 (rand()%100) < p，否则 0。"""
    return 1 if rng.randint(0, 99) < p else 0


def count_asked(menu_entries):
    """0x460500: 统计菜单条目表中 bit15 已置位的条目数。"""
    return sum(1 for w in menu_entries if (w & 0x8000))


def rand_avail(slots, rng):
    """0x460530: push 0xd ; call 0x4ebd60 -> i = rand()%13；若 slots[i]==0 则重试。"""
    if all(s == 0 for s in slots):
        return 0  # 退化保护：游戏保证至少 1 个可用
    while True:
        i = rng.randint(0, 0x7fffffff) % 13
        if slots[i] != 0:
            return i


def report_index(di, count, asked, flag6, flag8, slots, rng):
    """复刻 0x460420 的报告 handler 选取策略，返回 handler 索引 0..12。"""
    def prob(p):
        return prob_check(p, rng) != 0

    if di == 9:                              # 特殊类别（0x46042c cmp di,9）
        if count >= 3:                       # cmp word[0x513fcc],3 ; jae
            if asked == 1:
                return 0
            elif asked == 2:
                return 1
            elif asked == 3:
                return rand_avail(slots, rng)
            else:                            # asked >= 4 -> esi 保持 0
                return 0
        else:                                # count < 3
            if asked == 1:
                return 1 if prob(0x28) else 0   # 0x460499: 40% 取 handler 1
            else:
                return rand_avail(slots, rng)
    else:                                    # di != 9
        if asked == 1:
            if count > 1:
                return 1 if prob(0x28) else 0   # 0x460499 共享块
            # count <= 1 -> 落入 generic
        # generic (0x4604ad)
        if asked == 2 and count >= 2:
            if di == 0 or di == 1:
                return 12 if flag8 != 0 else rand_avail(slots, rng)   # 米価 handler 12
            elif di == 2:
                return 11 if flag6 != 0 else rand_avail(slots, rng)   # 馬販子 handler 11
            else:
                return rand_avail(slots, rng)
        else:
            return rand_avail(slots, rng)


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------
class SeqRng:
    """可控伪随机：依次吐出预设序列，便于确定性测试。"""
    def __init__(self, seq):
        self.seq = list(seq)
        self.i = 0
    def randint(self, lo, hi):
        v = self.seq[self.i % len(self.seq)]
        self.i += 1
        return v


def _sel(**kw):
    kw.setdefault("flag6", 0)
    kw.setdefault("flag8", 0)
    kw.setdefault("rng", random.Random(0))
    return report_index(**kw)


def self_test():
    ok = 0
    total = 0
    log = []
    def check(name, got, exp):
        nonlocal ok, total
        total += 1
        if got == exp:
            ok += 1
            log.append(f"[OK  ] {name}: got={got}")
        else:
            log.append(f"[FAIL] {name}: got={got} exp={exp}")

    # 1) di==9, count>=3, asked==1 -> 0
    check("d9 c>=3 a1", _sel(di=9, count=5, asked=1, slots=[1]*13, rng=SeqRng([0])), 0)
    # 2) di==9, count>=3, asked==2 -> 1
    check("d9 c>=3 a2", _sel(di=9, count=5, asked=2, slots=[1]*13, rng=SeqRng([0])), 1)
    # 3) di==9, count>=3, asked==3 -> rand_avail (确定性：rng 给 0 -> 取 slots[0])
    check("d9 c>=3 a3", _sel(di=9, count=5, asked=3, slots=[1]*13, rng=SeqRng([0])), 0)
    # 4) di==9, count>=3, asked>=4 -> 0
    check("d9 c>=3 a4", _sel(di=9, count=5, asked=4, slots=[1]*13, rng=SeqRng([0])), 0)
    # 5) di==9, count<3, asked==1, prob 不< 0x28(40) -> 0  (rand%100 = 40)
    check("d9 c<3 a1 lo", _sel(di=9, count=2, asked=1, slots=[1]*13, rng=SeqRng([40])), 0)
    # 6) di==9, count<3, asked==1, prob < 40 -> 1  (rand%100 = 39)
    check("d9 c<3 a1 hi", _sel(di=9, count=2, asked=1, slots=[1]*13, rng=SeqRng([39])), 1)
    # 7) di==9, count<3, asked!=1 -> rand_avail
    check("d9 c<3 a0", _sel(di=9, count=2, asked=0, slots=[1]*13, rng=SeqRng([0])), 0)
    # 8) di!=9, asked==1, count>1, prob < 40 -> 1  (rand%100 = 39)
    check("d!9 a1 c>1 hi", _sel(di=5, count=3, asked=1, slots=[1]*13, rng=SeqRng([39])), 1)
    # 9) di!=9, asked==1, count>1, prob 不< 40 -> 0  (rand%100 = 40)
    check("d!9 a1 c>1 lo", _sel(di=5, count=3, asked=1, slots=[1]*13, rng=SeqRng([40])), 0)
    # 10) di!=9, asked==1, count<=1 -> generic -> rand_avail
    check("d!9 a1 c<=1", _sel(di=5, count=1, asked=1, slots=[1]*13, rng=SeqRng([0])), 0)
    # 11) di==0, asked==2, count>=2, flag8!=0 -> 12 (米価)
    check("d0 a2 f8", _sel(di=0, count=2, asked=2, flag8=1, slots=[1]*13, rng=SeqRng([0])), 12)
    # 12) di==1, asked==2, count>=2, flag8!=0 -> 12
    check("d1 a2 f8", _sel(di=1, count=2, asked=2, flag8=1, slots=[1]*13, rng=SeqRng([0])), 12)
    # 13) di==0, asked==2, count>=2, flag8==0 -> rand_avail
    check("d0 a2 nof8", _sel(di=0, count=2, asked=2, flag8=0, slots=[1]*13, rng=SeqRng([3])), 3)
    # 14) di==2, asked==2, count>=2, flag6!=0 -> 11 (馬販子)
    check("d2 a2 f6", _sel(di=2, count=2, asked=2, flag6=1, slots=[1]*13, rng=SeqRng([0])), 11)
    # 15) di==2, asked==2, count>=2, flag6==0 -> rand_avail
    check("d2 a2 nof6", _sel(di=2, count=2, asked=2, flag6=0, slots=[1]*13, rng=SeqRng([3])), 3)
    # 16) di==7(其他), asked==2, count>=2 -> rand_avail
    check("d7 a2", _sel(di=7, count=2, asked=2, slots=[1]*13, rng=SeqRng([3])), 3)
    # 17) asked==0 (generic, 非 2) -> rand_avail
    check("a0", _sel(di=5, count=5, asked=0, slots=[1]*13, rng=SeqRng([3])), 3)
    # 18) rand_avail 只在非零槽里挑：slots 仅 [5]=1 -> 必返回 5  (rand%13 = 5)
    check("avail-only", _sel(di=5, count=5, asked=0,
                             slots=[0,0,0,0,0,1,0,0,0,0,0,0,0], rng=SeqRng([5])), 5)

    summary = f"self_test: {ok}/{total} {'ALL PASS' if ok==total else 'FAILED'}"
    log.append("")
    log.append(summary)
    with open(_ROOT + '/scripts/_report_selftest.txt', "w", encoding="utf-8") as f:
        f.write("\n".join(log) + "\n")
    print("\n".join(log))
    return ok == total


if __name__ == "__main__":
    import sys
    if "--dump" in sys.argv:
        print("report_index(...) 参考实现已加载；HANDLER_COUNT=%d" % HANDLER_COUNT)
    else:
        sys.exit(0 if self_test() else 1)
