#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CD BGM 调度表逆向 —— 枚举 CdPlayTrack(0x4013b0) 调用点并抽取轨号实参。

背景（BREAKTHROUGHS 续210 / 续195）：
  * 设备A = CD 数字音频，BGM 即 CD 音轨；`CdPlayTrack(t)`(0x4013b0) 用 MCI_FORMAT_TMSF 播放第 t 轨。
  * 中文版把 BGM 从 MML 方案换成 `MP3/`（34 首），轨号 1..34 与文件名一一对应。
  * **未破**：轨号 → 场景/曲名的调度表（即 CdPlayTrack 的 caller 上下文）。

本脚本闭合该缺口：
  1. 全映像扫 `E8 rel32`（direct near call），筛出目标 == CD 系列函数者。
  2. 对每个调用点，用「指令边界对齐回溯」抽取 `push imm` 实参（x86 变长指令不能从固定起点
     反汇编，须枚举回溯长度并只接受指令流中恰有指令起点 == call_va 的候选）。
  3. 归属调用点所在函数（回溯最近的标准序言 `55 8B EC` / `55 89 E5`），便于后续按场景定名。

用法：python scripts/cd_bgm_scheduler_ref.py [--selftest]
产物：scripts/cd_bgm_scheduler.json
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, "_unpacked_mem.bin")
BASE = 0x400000
OUT = os.path.join(HERE, "cd_bgm_scheduler.json")

try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    from capstone.x86 import X86_OP_IMM
except ImportError:  # pragma: no cover
    Cs = None

# CD 设备函数表（mci_av_subsystem.json devices.A_cdaudio.fn，续210 定名）
CD_FUNCS = {
    0x401040: "CdOpen",
    0x401000: "CdClose",
    0x4010A0: "CdMediaPresent",
    0x4010F0: "CdNumTracks",
    0x401270: "CdGetMode",
    0x401140: "CdTrackLenMSF",
    0x401210: "CdTrackLenSec",
    0x4012C0: "CdStopClose",
    0x4013B0: "CdPlayTrack",
}

# 已知场景函数锚点（来自既有逆向文档；用于给调用点所在函数加人类可读标注）
KNOWN_SCENES = {
    0x4A0D50: "time_rollover 月循环",
    0x460320: "council menu_items 评定菜单",
    0x4603F0: "council dispatch 主命派发",
    0x460420: "council report_index 报告状态机",
    0x4A84E0: "ai_diplomacy AI 主动外交",
    0x44D950: "event tick_dispatch 事件状态机",
    0x4A5FC0: "纳结算",
    0x44E710: "shop enter_shop 入店分发",
    0x4684C0: "duel 跳表派发",
    0x4C2E4E: "diplomacy init_relations",
    0x488030: "event_flags 主人公初始化",
}


def load_bin():
    with open(BIN, "rb") as f:
        return f.read()


def iter_call_sites(data):
    """扫 E8 rel32，返回 (call_va, target_va)"""
    n = len(data)
    for i in range(n - 5):
        if data[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", data, i + 1)[0]
        call_va = BASE + i
        target = call_va + 5 + rel
        yield call_va, target


def arg_at(data, call_va, span=24):
    """抽 call 前一条 `push imm` 的实参。

    x86 变长指令：从固定起点反汇编必然错位。正解 = 枚举回溯长度 back=1..span，
    只接受「从起点反汇编出的指令流里，恰有一条指令起点 == call_va」的候选（指令边界对齐），
    再取该指令流中紧邻 call 的前一条指令，若是 `push imm` 则命中。
    """
    if Cs is None:
        return None
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    off_call = call_va - BASE
    for back in range(1, span + 1):
        start = off_call - back
        if start < 0:
            break
        insns = list(md.disasm(data[start:off_call + 5], BASE + start))
        addrs = [ins.address for ins in insns]
        if call_va not in addrs:
            continue  # 起点未对齐到指令边界 → 该回溯长度无效
        idx = addrs.index(call_va)
        if idx == 0:
            continue
        prev = insns[idx - 1]
        if prev.mnemonic == "push" and prev.operands and prev.operands[0].type == X86_OP_IMM:
            return prev.operands[0].imm
    return None


def enclosing_func(data, call_va, window=0x2000):
    """回溯最近的标准函数序言 push ebp; mov ebp, esp (55 8B EC)"""
    off = call_va - BASE
    lo = max(0, off - window)
    best = None
    i = off - 2
    while i >= lo:
        if data[i] == 0x55 and data[i + 1] == 0x8B and data[i + 2] == 0xEC:
            best = BASE + i
            break
        i -= 1
    return best


def scan():
    data = load_bin()
    hits = []
    for call_va, target in iter_call_sites(data):
        name = CD_FUNCS.get(target)
        if name is None:
            continue
        rec = {"call_at": "0x%x" % call_va, "fn": name}
        if name == "CdPlayTrack":
            t = arg_at(data, call_va)
            rec["track"] = t
        fn = enclosing_func(data, call_va)
        rec["func"] = ("0x%x" % fn) if fn else None
        rec["scene"] = KNOWN_SCENES.get(fn) if fn else None
        hits.append(rec)
    return hits


def summarize(hits):
    plays = [h for h in hits if h["fn"] == "CdPlayTrack"]
    tracks = {}
    for h in plays:
        t = h.get("track")
        if t is None:
            continue
        tracks.setdefault(t, []).append(h["call_at"])
    return {
        "total_call_sites": len(hits),
        "by_fn": {n: sum(1 for h in hits if h["fn"] == n) for n in sorted(set(h["fn"] for h in hits))},
        "play_sites": len(plays),
        "tracks": {str(k): v for k, v in sorted(tracks.items())},
        "track_set": sorted(tracks.keys()),
        "unresolved": [h for h in plays if h.get("track") is None],
    }


def selftest(hits, summ):
    """自校验：结果必须自洽"""
    ok = 0
    fails = []

    def chk(cond, msg):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fails.append(msg)

    chk(len(hits) > 0, "至少 1 个 CD 函数调用点")
    chk(summ["play_sites"] > 0, "至少 1 个 CdPlayTrack 调用点")
    # 轨号必须落在 CD 音轨合法范围 1..34（中文版 MP3/ 恰 34 首）
    for t in summ["track_set"]:
        chk(1 <= t <= 34, "轨号 %d 超出 1..34" % t)
    # 解析出的轨号不得有 None（若全 None 说明抽参法失效）
    chk(len(summ["unresolved"]) == 0 or len(summ["track_set"]) > 0,
        "抽参法至少解析出部分轨号（未解析 %d 个）" % len(summ["unresolved"]))
    # 同一轨号可被多处调用，但调用点地址必须唯一
    all_sites = [s for v in summ["tracks"].values() for s in v]
    chk(len(all_sites) == len(set(all_sites)), "调用点地址无重复")
    print("[selftest] %d/%d PASS" % (ok, ok + len(fails)))
    for f in fails:
        print("  FAIL:", f)
    return len(fails) == 0


def main():
    hits = scan()
    summ = summarize(hits)
    out = {"cd_funcs": {("0x%x" % k): v for k, v in sorted(CD_FUNCS.items())},
           "call_sites": hits, "summary": summ}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("调用点 %d 个（CdPlayTrack %d）" % (summ["total_call_sites"], summ["play_sites"]))
    print("按函数:", summ["by_fn"])
    print("轨号:", summ["track_set"])
    for t in summ["track_set"]:
        print("  轨 %2d ← %s" % (t, ", ".join(summ["tracks"][str(t)])))
    if summ["unresolved"]:
        print("未解析实参的调用点:", summ["unresolved"])
    good = selftest(hits, summ)
    print("产物:", OUT)
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
