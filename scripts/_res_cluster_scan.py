# -*- coding: utf-8 -*-
"""
_res_cluster_scan.py  ——  资源加载簇全图探针（续196 前置）

目标：把「簇 handler → 资源表基址 → 文件名」的完整映射抓出来。
续161 只钉了 4 簇（0x492e20→0x506b20 / 0x493140→0x506b30 / 0x492f80→0x506b40 /
0x492ed0→0x506ba0），本脚本补全到全图。

管线（续162/163 已破）：
    簇 handler  →  push <资源表基址 VA> ; push <尺寸> ; call 0x4802e0
    0x4802e0(base, size) = memmove(0x522ca0, base, size) + call 0x4ec8c0(资源选择器构造器)
                           + movsx ecx,[esp+0x18]

stdcall 2 参：push 顺序右→左 ⇒ **call 前最后 1 个 push = arg0 = 资源表基址 VA**，
倒数第 2 个 = arg1 = 尺寸。

函数边界：用「全镜像 call/jmp 目标集」求最大 ≤va 者（比 prologue 模式稳健，
本 EXE 大量 FPO 函数无 `push ebp; mov ebp,esp`）。

用法:
    python3 scripts/_res_cluster_scan.py [目标函数VA(逗号分隔，默认 4802e0)]
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
import sys
import struct

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False


def rd(va, n):
    o = va - BASE
    if o < 0 or o + n > len(MEM):
        return b""
    return MEM[o:o + n]


def cstr(va, maxlen=32):
    b = rd(va, maxlen)
    z = b.find(b"\x00")
    if z >= 0:
        b = b[:z]
    try:
        return b.decode("ascii")
    except Exception:
        return b.decode("latin1")


def imm_of(op_str):
    out = []
    for t in op_str.split(","):
        t = t.strip()
        if re.fullmatch(r"(0x[0-9a-fA-F]+|[0-9]+)", t):
            out.append(int(t, 16) if t.lower().startswith("0x") else int(t))
    return out


# ---------------------------------------------------------------- 资源名全集
NAME_RE = re.compile(rb"[A-F]:[A-Z0-9_]{1,12}\.[A-Z0-9]{2,3}")


def scan_names():
    out = {}
    for m in NAME_RE.finditer(MEM):
        e = m.end()
        if e >= len(MEM) or MEM[e] != 0:
            continue
        out[BASE + m.start()] = m.group().decode("ascii")
    return out


NAMES = scan_names()
IMAGE_END = BASE + len(MEM)


def names_from_table(base_va, maxn=16):
    """从 base_va 起按 16B stride 读资源名，直到全零。"""
    got = []
    for k in range(maxn):
        va = base_va + 16 * k
        if not (BASE <= va < IMAGE_END):
            break
        if va in NAMES:
            got.append((k, va, NAMES[va]))
        else:
            b = rd(va, 16)
            if b == b"\x00" * 16:
                break
            got.append((k, va, "?<%s>" % b.hex()[:12]))
    return got


def real_names(base_va, maxn=16):
    return [n for (_k, _v, n) in names_from_table(base_va, maxn) if not n.startswith("?")]


# ---------------------------------------------------------------- 函数边界
def collect_call_targets():
    """全镜像 E8(rel32) + E9(rel32) 目标集 —— 用作函数入口候选。"""
    tg = set()
    for m in re.finditer(rb"[\xe8\xe9]", MEM):
        off = m.start()
        if off + 5 > len(MEM):
            continue
        rel = struct.unpack_from("<i", MEM, off + 1)[0]
        tgt = (BASE + off + 5 + rel) & 0xFFFFFFFF
        if BASE <= tgt < IMAGE_END:
            tg.add(tgt)
    return sorted(tg)


TARGETS = collect_call_targets()


def enclosing_fn(va, maxback=0x4000):
    """最大 call/jmp 目标 ≤ va 且距离在 maxback 内。"""
    lo = va - maxback
    best = None
    for t in TARGETS:
        if t > va:
            break
        if t >= lo:
            best = t
    return best


def pushes_before(call_va, span=0x60):
    """枚举回溯长度，只接受指令边界落在 call_va 的起点，取上下文最全者。"""
    best = None
    for back in range(1, span):
        start = call_va - back
        try:
            ins = list(md.disasm(rd(start, back + 16), start))
        except Exception:
            continue
        idx = None
        for k, i in enumerate(ins):
            if i.address == call_va:
                idx = k
                break
        if idx is None:
            continue
        pushes = []
        for i in ins[:idx]:
            if i.mnemonic == "push":
                v = imm_of(i.op_str)
                if v:
                    pushes.append((i.address, v[0]))
        if pushes:
            if best is None or back > best[0]:
                best = (back, pushes)
    return best[1] if best else []


def find_calls(tgts):
    calls = []
    off = 0
    while True:
        i = MEM.find(b"\xE8", off)
        if i < 0:
            break
        rel = struct.unpack_from("<i", MEM, i + 1)[0]
        tgt = (BASE + i + 5 + rel) & 0xFFFFFFFF
        if tgt in tgts:
            calls.append(BASE + i)
        off = i + 1
    return calls


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "4802e0"
    tgts = set(int(t, 16) for t in arg.split(","))

    print("=" * 100)
    print("资源加载簇全图探针  ——  call 目标: %s" % ", ".join("0x%x" % t for t in sorted(tgts)))
    print("资源名全集 %d 个 ｜ 函数入口候选 %d 个" % (len(NAMES), len(TARGETS)))
    print("=" * 100)

    calls = find_calls(tgts)
    print("命中 call 站点: %d 处\n" % len(calls))

    rows = []
    for va in calls:
        fn = enclosing_fn(va)
        pushes = pushes_before(va)
        base_va = size = None
        if pushes:
            last = pushes[-1][1]
            prev = pushes[-2][1] if len(pushes) >= 2 else None
            # 最后一个 push 若是映像内地址 ⇒ arg0=资源表基址
            if BASE <= last < IMAGE_END:
                base_va, size = last, prev
            elif prev is not None and BASE <= prev < IMAGE_END:
                base_va, size = prev, last
        rows.append((va, fn, base_va, size, pushes))

    for (va, fn, base_va, size, pushes) in rows:
        tag = ""
        if base_va:
            ns = real_names(base_va, 10)
            if ns:
                tag = " => %s" % " / ".join(ns)
            elif base_va in NAMES:
                tag = " => (单名) %s" % NAMES[base_va]
            else:
                tag = " => (表 0x%06x 内无名串)" % base_va
        print("  0x%06x  fn=0x%06x  base=%s size=%s%s" % (
            va, fn or 0,
            ("0x%06x" % base_va) if base_va else "--",
            ("0x%x" % size) if size is not None else "--",
            tag))

    # ---------------------------------------------------------- 聚合：表 → 引用函数
    print("\n" + "=" * 100)
    print("聚合 A：资源表基址 -> 引用它的函数（= 哪些簇加载它）")
    print("=" * 100)
    tbl = {}
    for (va, fn, base_va, size, pushes) in rows:
        if not base_va:
            continue
        ns = real_names(base_va, 10) or ([NAMES[base_va]] if base_va in NAMES else [])
        if ns:
            tbl.setdefault(base_va, (ns, set()))[1].add(fn)
    for pv in sorted(tbl):
        ns, fns = tbl[pv]
        print("  0x%06x  %-52s <- %s" % (
            pv, " / ".join(ns)[:52], ", ".join("0x%06x" % (f or 0) for f in sorted(fns))))

    # ---------------------------------------------------------- 聚合：簇 → 资源
    print("\n" + "=" * 100)
    print("聚合 B：簇 handler 函数 -> 它加载的资源")
    print("=" * 100)
    f2r = {}
    for (va, fn, base_va, size, pushes) in rows:
        if not base_va or fn is None:
            continue
        ns = real_names(base_va, 10) or ([NAMES[base_va]] if base_va in NAMES else [])
        if ns:
            f2r.setdefault(fn, set()).update(ns)
    for fn in sorted(f2r):
        print("  0x%06x -> %s" % (fn, " / ".join(sorted(f2r[fn]))))

    # ---------------------------------------------------------- 覆盖统计
    print("\n" + "=" * 100)
    print("覆盖统计")
    print("=" * 100)
    covered = set()
    for (va, fn, base_va, size, pushes) in rows:
        if not base_va:
            continue
        for (_k, v, n) in names_from_table(base_va, 10):
            if not n.startswith("?"):
                covered.add(v)
    print("  经 0x4802e0 管线显式加载的资源名: %d / %d" % (len(covered), len(NAMES)))
    missing = [(v, n) for v, n in sorted(NAMES.items()) if v not in covered]
    print("  未覆盖 %d 个:" % len(missing))
    for v, n in missing:
        print("     0x%06x  %s" % (v, n))


if __name__ == "__main__":
    main()
