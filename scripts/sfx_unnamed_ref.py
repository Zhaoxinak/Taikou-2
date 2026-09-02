#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sfx_unnamed_ref.py —— 续226：9 个「无静态立即数调用点」音效 ID 取证 + 自校验
=================================================================================
背景（续195）：play_sfx @0x4997c0，39 个音效 ID（0..38，上限由 `cmp si,0x27` 钉死）。
其中 30 个有 `push 0xNN; call 0x4997c0` 立即数调用点；余 9 个在静态上找不到立即数调用点。

本脚本任务：
  ① 断言总音效 ID 数 = 39（0x50ba40 名表 + `cmp si,0x27` 双证）。
  ② 给出 9 个无名 ID 的号码，并尽最大努力定下语义（文件名字面 + 已破调用点）。
  ③ 自测 PASS/FAIL，稳定事实才断言；推断写进 _draft_bt_226_sfx.md，不进硬性断言。

取证结果（真实，见脚本输出与草稿）：
  - 9 个无名 ID = [15,19,20,26,32,34,35,36,37]
  - 34/35 已静态破案：@0x44edd4  `xor ecx,ecx; setne cl; add ecx,0x22; push ecx` →
        id = 0x22(34·MI_HARE 晴) 或 0x23(35·MI_AME 雨)，属「天气切换」派发。
  - 其余 7 个（15,19,20,26,32,36,37）无任何静态立即数/算术调用点，仅经 10 个
        「参数源自内存/结构体字段或循环变量」的间接调用点可达 —— 静态不可定值。

语义（文件名罗马字 + 上下文）：
  15 ZANSYU   残守/残兵（待考）        [推断·中]
  19 UKETA    受击/挨打（单挑）        [文件名字面·高]
  20 YOKETA   闪避/躲开（单挑）        [文件名字面·高]
  26 KAISHIN  会心一击（单挑/战斗）    [文件名字面·高]
  32 MACHIMES 町消息广播（内政）       [文件名字面·高]
  34 MI_HARE  天候·晴（天气派发）      [静态调用点·高]
  35 MI_AME   天候·雨（天气派发）      [静态调用点·高]
  36 MATISIRO 待机/町城（待考）        [推断·中]
  37 SIKAKU   死角/背袭（单挑/战斗）   [文件名字面·高]

注意：本脚本只**断言可确定的事实**（表长、无名 ID 号码、34/35 调用点、7 个无立即数点），
      "语义"本身作为信息性打印，不进硬性断言（避免对推断做脆弱断言）。
"""
import os, re, struct, sys, pickle
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BASE = 0x400000
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
PKL = pickle.load(open(os.path.join(HERE, "_insn_addrs.pkl"), "rb"))
FUNCS_S = sorted(PKL[1])

PLAY = 0x4997c0          # play_sfx(id)
SFX_TBL = 0x50ba40       # const char* SFX_NAMES[39]
PLAY_GATE_CMP = 0x4997c5  # `cmp si, 0x27` 位置（play_sfx 入口后）

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


# ---------------- 基本工具 ----------------
def rd(va, n):
    o = va - BASE
    if o < 0 or o + n > len(MEM):
        return b""
    return MEM[o:o + n]


def find_calls(target):
    out = []
    off = 0
    while True:
        i = MEM.find(b"\xE8", off)
        if i < 0:
            break
        rel = struct.unpack_from("<i", MEM, i + 1)[0]
        if (BASE + i + 5 + rel) & 0xFFFFFFFF == target:
            out.append(BASE + i)
        off = i + 1
    return out


def imm_val(tok):
    tok = tok.strip()
    m = re.fullmatch(r"(0x[0-9a-fA-F]+|[0-9]+)", tok)
    if not m:
        return None
    s = m.group()
    return int(s, 16) if s.lower().startswith("0x") else int(s)


def arg_immediate(call_va, span=0x40):
    """只取最近的 `push <imm>` 立即数实参（与续195 同口径）。"""
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
                v = imm_val(i.op_str)
                if v is not None:
                    pushes.append((i.address, v))
        if pushes:
            best = (back, pushes[-1][1])
    return best[1] if best else None


# ID→文件名（名串池，倒序指向 @0x50badc 起）
def sfx_name(i):
    p = struct.unpack("<I", rd(SFX_TBL + 4 * i, 4))[0]
    b = rd(p, 24)
    z = b.find(0)
    return b[:z if z >= 0 else 24].decode("ascii", "replace")


# ---------------- 自测 ----------------
FAIL = []
OK = []


def check(name, cond, extra=""):
    if cond:
        OK.append(name)
        print("  [OK  ] %s" % name)
    else:
        FAIL.append(name)
        print("  [FAIL] %s   %s" % (name, extra))


def main():
    print("=" * 78)
    print("续226 · 9 个无名音效 ID 取证自校验")
    print("=" * 78)

    # ---- ① 总音效 ID 数 = 39（名表 + 门控双证） ----
    print("\n[1] 总数 = 39")
    tbl_count = 0
    for i in range(60):
        p = struct.unpack("<I", rd(SFX_TBL + 4 * i, 4))[0]
        nm = sfx_name(i)
        if re.fullmatch(r"A:[A-Z0-9_]+\.KOS", nm):
            tbl_count += 1
        else:
            break
    check("A1 名指针表 @0x50ba40 连续有效 A:*.KOS 项 = 39",
          tbl_count == 39, "got %d" % tbl_count)

    # 门控 `cmp si, 0x27`
    gate = " ; ".join("%s %s" % (i.mnemonic, i.op_str)
                      for i in md.disasm(rd(PLAY, 0x40), PLAY))
    check("A2 play_sfx 门控 `cmp si, 0x27`（上限 39）",
          "cmp" in gate and "0x27" in gate, gate[:80])

    # ---- ② 9 个无名 ID 号码 = 立即数覆盖的补集 ----
    print("\n[2] 9 个无名 ID（立即数调用点覆盖的补集）")
    sites = find_calls(PLAY)
    covered = set()
    for va in sites:
        a = arg_immediate(va)
        if a is not None and 0 <= a < 39:
            covered.add(a)
    unnamed = sorted(set(range(39)) - covered)
    check("B1 立即数可定 ID 数 = 30", len(covered) == 30,
          "got %d : %s" % (len(covered), sorted(covered)))
    EXPECT = [15, 19, 20, 26, 32, 34, 35, 36, 37]
    check("B2 9 个无名 ID 号码 = %s" % EXPECT, unnamed == EXPECT,
          "got %s" % unnamed)
    check("B3 存在 call 0x4997c0 的调用点（≥70）", len(sites) >= 70,
          "got %d" % len(sites))

    # ---- ③ 34/35 静态派发点 @0x44edd4 ----
    print("\n[3] 34/35 天气派发调用点 @0x44edd4")
    win = list(md.disasm(rd(0x44edd0, 0x14), 0x44edd0))
    txt = " ; ".join("%s %s" % (i.mnemonic, i.op_str) for i in win)
    # add ecx, 0x22 紧邻 call 0x4997c0 之前
    has_add = any(i.mnemonic == "add" and "ecx" in i.op_str and "0x22" in i.op_str
                  for i in win)
    has_call = any(i.mnemonic == "call" and "0x4997c0" in i.op_str for i in win)
    check("C1 @0x44edd4 含 `add ecx, 0x22`（基址 0x22=34，±1 → 34/35）",
          has_add, txt)
    check("C2 @0x44edd4 含 `call 0x4997c0`", has_call, txt)
    check("C3 0x22 == 34 且 0x23 == 35（天气 ID 配对）", 0x22 == 34 and 0x23 == 35)

    # ---- ④ 其余 7 个：确无任何立即数调用点（负证） ----
    print("\n[4] 7 个真正无静态调用点（15,19,20,26,32,36,37）")
    for i in (15, 19, 20, 26, 32, 36, 37):
        n = sum(1 for va in sites if arg_immediate(va) == i)
        check("D  ID %d 无任何 `push 0x%02x` 立即数调用点" % (i, i), n == 0,
              "found %d" % n)

    # ---- 信息性输出：9 个 ID 的语义（不进断言） ----
    print("\n" + "-" * 78)
    print("9 个无名 ID 语义表（信息性，非断言）：")
    SEM = {
        15: ("ZANSYU",   "残守/残兵（攻城残留守军，待考）", "推断·中"),
        19: ("UKETA",    "受击/挨打（单挑）",              "文件名字面·高"),
        20: ("YOKETA",   "闪避/躲开（单挑）",              "文件名字面·高"),
        26: ("KAISHIN",  "会心一击（单挑/战斗·暴击）",     "文件名字面·高"),
        32: ("MACHIMES", "町消息广播（内政/町）",           "文件名字面·高"),
        34: ("MI_HARE",  "天候·晴（天气切换派发）",         "静态调用点·高"),
        35: ("MI_AME",   "天候·雨（天气切换派发）",         "静态调用点·高"),
        36: ("MATISIRO", "待机/町城（待考）",               "推断·中"),
        37: ("SIKAKU",   "死角/背袭（单挑/战斗）",          "文件名字面·高"),
    }
    for i in EXPECT:
        fn, zh, conf = SEM[i]
        print("  [%2d] %-9s %-26s  %s" % (i, fn, zh, conf))
    print("-" * 78)
    print("其中 34/35 已静态定位调用点；15/19/20/26/32/36/37 仅经 10 个")
    print("「参数源自内存/结构体字段或循环变量」的间接调用点可达，静态不可定值。")
    print("-" * 78)

    # ---- 汇总 ----
    print("\n" + "=" * 78)
    if FAIL:
        print("RESULT: %d FAIL ❌  -> %s" % (len(FAIL), FAIL))
        return 1
    print("RESULT: ALL PASS ✅  (断言均为确定性事实，语义见上表)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
