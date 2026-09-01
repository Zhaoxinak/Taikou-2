# -*- coding: utf-8 -*-
"""内政大模块 —— 城字段饱和增量包装器的调用点扫描（续153）

包装器（续140 实体字段增量族；本模块中 ecx = 城表记录 @0x51eb88）：
  0x4a32a0 -> +0x0c cap 100   (农商)
  0x4a32c0 -> +0x0d cap 250   (守城度)
  0x4a3310 -> +0x0e cap 200   (民心/治安)
  0x4a3360 -> +0x0f cap 100   (生产率)
  0x4a33a0 -> +0x10 cap 50000 (軍糧)
  0x4a33f0 -> +0x12 cap 30000 (米)
  0x4a3440 -> +0x14 cap 30000 (資金)
  0x4a3490 -> +0x16 cap 2000
  0x4a34e0 -> +0x18 cap 2000
  0x4a3530 -> +0x1a cap 200   (次级民情)

用法:
  python3.7 _naisei_scan.py             # 列出全部调用点 + 所在函数
  python3.7 _naisei_scan.py -f 0x4a5c80 # 反汇编某函数
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

import sys
from capstone import *

MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', "rb").read()
BASE = 0x400000
TEXT_LO, TEXT_HI = 0x401000, 0x4f0000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

WRAPPERS = {
    0x4a32a0: ("+0x0c", 100, "农商"),
    0x4a32c0: ("+0x0d", 250, "守城度"),
    0x4a3310: ("+0x0e", 200, "民心/治安"),
    0x4a3360: ("+0x0f", 100, "生产率"),
    0x4a33a0: ("+0x10", 50000, "軍糧"),
    0x4a33f0: ("+0x12", 30000, "米"),
    0x4a3440: ("+0x14", 30000, "資金"),
    0x4a3490: ("+0x16", 2000, "?"),
    0x4a34e0: ("+0x18", 2000, "?"),
    0x4a3530: ("+0x1a", 200, "次级民情"),
}


def all_call_targets():
    """函数起点种子：所有 call rel32 目标（+ 若干入口）。"""
    seeds = set()
    n = len(MEM)
    for i in range(TEXT_LO - BASE, TEXT_HI - BASE - 5):
        if MEM[i] == 0xE8:
            rel = int.from_bytes(MEM[i + 1:i + 5], "little", signed=True)
            tgt = BASE + i + 5 + rel
            if TEXT_LO <= tgt < TEXT_HI:
                seeds.add(tgt)
    return sorted(seeds)


FUNC_STARTS = None
FUNC_SET = None


def _init_funcs():
    global FUNC_STARTS, FUNC_SET
    if FUNC_STARTS is None:
        FUNC_STARTS = all_call_targets()
        FUNC_SET = set(FUNC_STARTS)


def caller_func(va):
    """返回 va 所在函数的起点 VA（不超过 0x4000 字节回溯）。"""
    _init_funcs()
    import bisect
    i = bisect.bisect_right(FUNC_STARTS, va) - 1
    best = FUNC_STARTS[i]
    # 向前找最近的、且函数体确实覆盖 va 的起点
    for k in range(i, max(0, i - 200), -1):
        s = FUNC_STARTS[k]
        if va - s > 0x6000:
            break
        # 粗判：从 s 线性反汇编到 va，看是否可达
        if _reaches(s, va):
            return s
    return best


def _reaches(start, target, limit=0x6000):
    code = MEM[start - BASE: target - BASE + 16]
    for ins in md.disasm(code, start):
        if ins.address >= target:
            return True
        if ins.mnemonic in ("ret", "jmp") and ins.address > start:
            # 无条件跳走 / 返回：到此为止
            pass
        if ins.address - start > limit:
            return False
    return False


def disas_fn(va, maxlen=0x800, stop_ret=True):
    """从 va 反汇编到下一个函数起点（stop_ret=False 时不因 ret 提前停）。"""
    _init_funcs()
    import bisect
    i = bisect.bisect_right(FUNC_STARTS, va)
    end = FUNC_STARTS[i] if i < len(FUNC_STARTS) else TEXT_HI
    end = min(end, va + maxlen)
    code = MEM[va - BASE: end - BASE]
    out = []
    for ins in md.disasm(code, va):
        out.append(ins)
        if stop_ret and ins.mnemonic == "ret":
            break
    return out


def find_calls(targets):
    res = {t: [] for t in targets}
    n = len(MEM)
    for i in range(TEXT_LO - BASE, TEXT_HI - BASE - 5):
        if MEM[i] == 0xE8:
            rel = int.from_bytes(MEM[i + 1:i + 5], "little", signed=True)
            callee = BASE + i + 5 + rel
            if callee in res:
                res[callee].append(BASE + i)
    return res


def main():
    if len(sys.argv) > 2 and sys.argv[1] in ("-f", "-F"):
        va = int(sys.argv[2], 16)
        for ins in disas_fn(va, maxlen=0x2000, stop_ret=(sys.argv[1] == "-f")):
            print("0x%06x  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
        return

    calls = find_calls(WRAPPERS)
    # 按所在函数聚合
    from collections import defaultdict
    fnmap = defaultdict(list)   # func -> [(wrapper, callsite)]
    for w, sites in calls.items():
        for s in sites:
            fnmap[caller_func(s)].append((w, s))
    print("== 城字段增量包装器调用点（按所在函数聚合）== 共 %d 个函数" % len(fnmap))
    for fn in sorted(fnmap):
        ws = sorted(set(w for w, _ in fnmap[fn]))
        desc = ", ".join("%s%s(%s)" % (WRAPPERS[w][0], "" , WRAPPERS[w][2]) for w in ws)
        print("0x%06x  n=%2d  %s" % (fn, len(fnmap[fn]), desc))


if __name__ == "__main__":
    main()
