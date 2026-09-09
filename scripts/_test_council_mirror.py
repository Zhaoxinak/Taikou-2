# -*- coding: utf-8 -*-
"""
_test_council_mirror.py — council.gd 的 Python 等价镜像（验证逻辑与期望值）
复刻 scripts/council_ref.py + scripts/council_report_ref.py（0x460420 报告选取状态机等）。
本机 Godot --script 主循环失效，故用 Python 复跑同一套断言验证 GDScript 移植的算法正确性。
运行：python3 scripts/_test_council_mirror.py
"""
HANDLER_COUNT = 13
FLAG_ASKED = 0x8000
ID_MERCHANT = 17
ID_CASTLE = 22

TASK_NAMES = ["贩卖军粮", "购买军粮", "军马", "洋枪", "开垦农田", "改建",
              "筑城", "进贡", "威吓", "朝廷工作", "收集情报", "谋略"]

REPORT_MSG = {1: 0x1202, 2: 0x1203, 3: 0x1204, 4: 0x1205, 5: 0x1206, 6: 0x1207,
              7: 0x1208, 8: 0x1209, 9: 0x120A, 10: 0x120B, 11: 0x120C, 12: 0x120E}

STR_MERCHANT = "商　人"
STR_STOP = "停　止"


def report_msg_id(idx):
    return REPORT_MSG.get(idx, -1)


def count_asked(menu_entries):
    return sum(1 for w in menu_entries if int(w) & FLAG_ASKED)


def rand_avail(slots, rng):
    if len(slots) == 0:
        return 0
    if all(int(s) == 0 for s in slots):
        return 0
    while True:
        i = int(rng(13)) % 13
        if 0 <= i < len(slots) and int(slots[i]) != 0:
            return i


def report_index(di, count, asked, flag6, flag8, slots, rng):
    if di == 9:
        if count >= 3:
            if asked == 1:
                return 0
            elif asked == 2:
                return 1
            elif asked == 3:
                return rand_avail(slots, rng)
            else:
                return 0
        else:
            if asked == 1:
                return 1 if rng(100) < 0x28 else 0
            else:
                return rand_avail(slots, rng)
    else:
        if asked == 1:
            if count > 1:
                return 1 if rng(100) < 0x28 else 0
        if asked == 2 and count >= 2:
            if di == 0 or di == 1:
                return 12 if flag8 != 0 else rand_avail(slots, rng)
            elif di == 2:
                return 11 if flag6 != 0 else rand_avail(slots, rng)
            else:
                return rand_avail(slots, rng)
        else:
            return rand_avail(slots, rng)


def target_name(target_id, resolver=None):
    i = int(target_id) & 0xFFFF
    if i == ID_MERCHANT:
        return STR_MERCHANT
    if i < 1000:
        if resolver is not None:
            r = resolver(target_id)
            if r:
                return r
        return ""
    if i < 2000:
        if resolver is not None:
            r = resolver(target_id)
            if r:
                return r
        return "NPC%d" % i
    if i < 3000:
        return "NPC%d" % i
    if resolver is not None:
        r = resolver(target_id)
        if r:
            return r
    return "NPC%d" % i


def slot_label(entry_id, target_words=None, resolver=None):
    target_words = target_words or []
    e = int(entry_id) & 0x7FFF
    if e == ID_MERCHANT:
        return STR_MERCHANT
    if e < 30:
        tid = target_words[e] if e < len(target_words) else 0
        return target_name(tid, resolver)
    return ""


def menu_items(entries, target_words=None, resolver=None):
    return [slot_label(int(e), target_words, resolver) for e in entries] + [STR_STOP]


def dispatch(entry_id):
    e = int(entry_id) & 0x7FFF
    if e == ID_CASTLE:
        return {"kind": "special_22"}
    return {"kind": "handler"}


class SeqRng:
    def __init__(self, seq):
        self.seq = list(seq)
        self.i = 0
    def __call__(self, n):
        v = self.seq[self.i % len(self.seq)]
        self.i += 1
        return v


def _run_tests():
    ok = total = 0
    def check(name, got, exp):
        nonlocal ok, total
        total += 1
        if got == exp:
            ok += 1
        else:
            print(f"  FAIL: {name}: got={got!r} exp={exp!r}")

    S = [1] * 13
    check("HANDLER_COUNT", HANDLER_COUNT, 13)
    check("TASK_NAMES", TASK_NAMES[0], "贩卖军粮")
    check("report_msg_id(1)", report_msg_id(1), 0x1202)
    check("report_msg_id(12)", report_msg_id(12), 0x120E)
    check("report_msg_id(0)", report_msg_id(0), -1)
    check("STR", (STR_MERCHANT, STR_STOP), ("商　人", "停　止"))

    check("count_asked", count_asked([5, 0x8005, 0x8001]), 2)
    check("count_asked0", count_asked([1, 2, 3]), 0)
    check("rand_avail0", rand_avail(S, SeqRng([0])), 0)
    check("rand_avail_only5", rand_avail([0,0,0,0,0,1,0,0,0,0,0,0,0], SeqRng([5])), 5)
    check("rand_avail_zero", rand_avail([0]*13, SeqRng([0])), 0)

    # report_index 18 例
    check("d9 c>=3 a1", report_index(9, 5, 1, 0, 0, S, SeqRng([0])), 0)
    check("d9 c>=3 a2", report_index(9, 5, 2, 0, 0, S, SeqRng([0])), 1)
    check("d9 c>=3 a3", report_index(9, 5, 3, 0, 0, S, SeqRng([0])), 0)
    check("d9 c>=3 a4", report_index(9, 5, 4, 0, 0, S, SeqRng([0])), 0)
    check("d9 c<3 a1 lo", report_index(9, 2, 1, 0, 0, S, SeqRng([40])), 0)
    check("d9 c<3 a1 hi", report_index(9, 2, 1, 0, 0, S, SeqRng([39])), 1)
    check("d9 c<3 a0", report_index(9, 2, 0, 0, 0, S, SeqRng([0])), 0)
    check("d!9 a1 c>1 hi", report_index(5, 3, 1, 0, 0, S, SeqRng([39])), 1)
    check("d!9 a1 c>1 lo", report_index(5, 3, 1, 0, 0, S, SeqRng([40])), 0)
    check("d!9 a1 c<=1", report_index(5, 1, 1, 0, 0, S, SeqRng([0])), 0)
    check("d0 a2 f8", report_index(0, 2, 2, 0, 1, S, SeqRng([0])), 12)
    check("d1 a2 f8", report_index(1, 2, 2, 0, 1, S, SeqRng([0])), 12)
    check("d0 a2 nof8", report_index(0, 2, 2, 0, 0, S, SeqRng([3])), 3)
    check("d2 a2 f6", report_index(2, 2, 2, 1, 0, S, SeqRng([0])), 11)
    check("d2 a2 nof6", report_index(2, 2, 2, 0, 0, S, SeqRng([3])), 3)
    check("d7 a2", report_index(7, 2, 2, 0, 0, S, SeqRng([3])), 3)
    check("a0", report_index(5, 5, 0, 0, 0, S, SeqRng([3])), 3)
    check("avail-only", report_index(5, 5, 0, 0, 0, [0,0,0,0,0,1,0,0,0,0,0,0,0], SeqRng([5])), 5)

    # routing
    res = lambda v: ("武将%d" % v) if v < 1000 else ""
    check("target_name(17)", target_name(17), "商　人")
    check("target_name(0)", target_name(0, res), "武将0")
    check("target_name(1000)", target_name(1000, res), "NPC1000")
    check("target_name(3000)", target_name(3000, res), "NPC3000")
    check("menu_items", menu_items([0, 1, 17], [0, 1000], res), ["武将0", "NPC1000", "商　人", "停　止"])
    check("dispatch(22)", dispatch(22)["kind"], "special_22")
    check("dispatch(5)", dispatch(5)["kind"], "handler")

    print(f"\nRESULT: {ok}/{total} checks passed (council mirror)")
    return ok == total


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_tests() else 1)
