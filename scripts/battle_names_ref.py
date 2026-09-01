# -*- coding: utf-8 -*-
"""
battle_names_ref.py  —  兵种/阵形/计略 名称 参考 + 静态缺席验证
================================================================
承接清单 P1「兵种/阵形/计略 中文名 → 非 EXE 静态、非 MSGX；emu 捕获渲染前
字符串指针或查精灵 label」。

本脚本做两件事：
  (1) **负向自测**：对 EXE(`_unpacked_mem.bin`) 与 `Taikou2 Original/` 下所有
      资源文件做 cp932(Shift-JIS) 字符串抽取，断言 9 阵形 / 兵种 / 计略 的
      **具体名称字符串在静态二进制中完全不存在**（0 命中）—— 复现并钉死
      「名称非静态文本」这一结论，排除「暴力扫字符串」这条走不通的路。
  (2) **参考表**：给出太閤立志伝2 公开资料中常见的 阵形/兵种/计略 名称，
      作为复刻工程的**对照参考**。⚠️ 这些来自外部领域知识，**并非本逆向产物**；
      真正的「类型索引 → 名称」绑定须由 emu 在战斗渲染路径上捕获字符串指针
      （或 dump 精灵 label）坐实，本脚本不声称已逆向出该绑定表。

运行：python battle_names_ref.py   （从 scripts/ 目录）
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

import os, glob, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin')
ORIG = os.path.join(os.path.dirname(HERE), "Taikou2 Original")

# ---- cp932 字符串抽取 ----
def sjis_runs(b):
    out = []
    i, n = 0, len(b)
    cur = bytearray(); cur_start = -1
    def flush():
        nonlocal cur, cur_start
        if len(cur) >= 2:
            try:
                out.append(cur.decode("cp932"))
            except Exception:
                pass
        cur.clear(); cur_start = -1
    while i < n:
        c = b[i]
        if (0x81 <= c <= 0x9F or 0xE0 <= c <= 0xEF) and i + 1 < n:
            t = b[i+1]
            if 0x40 <= t <= 0xFC and t != 0x7F:
                if cur_start < 0: cur_start = i
                cur += bytes([c, t]); i += 2; continue
        flush(); i += 1
    flush()
    return out

# ---- 具体、无歧义的名称（若静态存在则必为战斗名）----
SPECIFIC = [
    # 9 阵形
    "鶴翼","魚鱗","偃月","方円","鋒矢","長蛇","車懸","藤蔓","北斗","蓮華",
    # 兵种
    "足軽","騎馬","鉄砲","鉄炮","水軍","洋槍",
    # 计略（战术）
    "火計","伏兵","斎壇","斉壇","影武者","流言","募兵","十文字","釣瓶",
    "威圧","混乱","突撃","防柵","空城","背水","籠城","撹乱","煽動","戦法","陣形",
]

def scan_file(path):
    try:
        b = open(path, "rb").read()
    except Exception:
        return set()
    hits = set()
    for s in sjis_runs(b):
        for k in SPECIFIC:
            if k in s:
                hits.add(k)
    return hits

def main():
    # (1) 负向自测：EXE
    exe_hits = scan_file(BIN)
    # (1b) 资源文件（原始未解压，cp932 抽不到 LZW 内容属预期；此处只查能抽到者）
    res_hits = set()
    if os.path.isdir(ORIG):
        for f in glob.glob(os.path.join(ORIG, "*")):
            res_hits |= scan_file(f)
    all_hits = exe_hits | res_hits
    print(f"[static scan] EXE specific-name hits = {len(exe_hits)} ; resource hits = {len(res_hits)}")
    print(f"  EXE: {sorted(exe_hits)}")
    print(f"  RES: {sorted(res_hits)}")
    ok = (len(all_hits) == 0)
    print(f"  [{'PASS' if ok else 'FAIL'}] 具体战斗名称在静态二进制中完全缺席 (非 EXE 静态文本)")

    # (2) 参考表（外部领域知识，非逆向产物——仅作复刻对照）
    formations = ["鶴翼","魚鱗","偃月","方円","鋒矢","長蛇","車懸","藤蔓","北斗"]
    unit_types = ["足軽","足軽組頭","騎馬","騎馬組頭","鉄砲","鉄砲組頭","弓","弓組頭","水軍","水軍組頭"]
    tactics = ["火計","伏兵","斎壇","影武者","流言","募兵","十文字","釣瓶","威圧","混乱",
               "突撃","防柵","空城","背水","籠城","撹乱","煽動"]
    print("\n[参考表·外部领域知识·须运行时确认]")
    print("  9 陣形:", " / ".join(formations))
    print("  兵种(身份):", " / ".join(unit_types))
    print("  計略(示例):", " / ".join(tactics))
    print("\n  ⚠️ 以上为太閤立志伝2 公开资料常见内容，非本逆向提取；")
    print("     索引→名称 绑定须 emu 捕获战斗渲染路径字符串指针 / 精灵 label 坐实。")

    # 汇总
    total = 1
    passed = 1 if ok else 0
    print(f"\n==== SUMMARY: {passed}/{total} PASS (负向验证) ====")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
