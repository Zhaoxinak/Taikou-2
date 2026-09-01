#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
resource_manifest_ref.py -- 太阁立志传2「原版资源/素材清单」全破参考实现（续195）
=====================================================================================
模块定位：项目此前只零散记录了 5 张资源阵列 / 6 个表名（续161、续163），从未把
**EXE 内嵌的全部原版资源名** 枚举干净。本模块完成：

  ① 全镜像扫描 `X:NAME.EXT` 资源名 → **90 个**（此前未知总数）
  ② 聚类成 **16 组阵列**（主阵列 stride 16B，音效区为「名串池 + 39 项指针表」双结构）
  ③ 定位每个资源的 **加载点函数**（`call 0x4802e0` 资源加载器 / `call 0x4ec8c0` 选择器构造器
     / 直接字面引用），建「资源 → 加载函数 → 类别」映射
  ④ 与原版目录 `Taikou2 Original/` 的 **110 个文件** 交叉对照，标出
     「EXE 引用但目录缺失」与「目录有但 EXE 未引用」

────────────────────────── 资源加载管线（沿用续161/162/163）───────────────────────────
  0x4802e0(base, size) : 资源加载器 —— push <资源名地址>; push <size>; call 0x4802e0
                        （内部 memmove(0x522ca0, base, 0x20) + call 0x4ec8c0）
  0x4ec8c0(name)       : 资源选择器构造器 —— 剥 `X:` 前缀，`and al,0xfb`，
                        `cmp eax,3; ja` 跳表 0x4ec948 决定尺寸 0/1/2/0x1000，`call [0x4fb07c]` 注册
  0x492800(a,b,c)      : 3 参转发到 memmove 0x4f40b0
  0x4015f0(name,0,0)   : 音效播放底层（cdecl 3 参），由 play_sfx 0x4997c0 调用

⚠️ 工具坑（本模块实测，与 sfx_subsystem_ref 同源）：
  - 抽 `call` 的实参**不能**从单一固定起点反汇编（x86 变长指令会错位，实测会 0 命中）。
    正解 = 枚举回溯长度 back=1..span，只接受「指令流中存在 address==call_va」的起点，
    取 back 最大者。见 pushes_before()。
  - 资源名正则须限定 `[A-F]:` 盘符前缀且紧跟 NUL，否则会把数据字节误判为名串。

自校验：见 main()（M1–M9）。输出：scripts/resource_manifest.json
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

import os, re, struct, sys, json
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, _ROOT + '/scripts/_unpacked_mem.bin')
ORIG_DIR = os.path.join(ROOT, "Taikou2 Original")
BASE = 0x400000

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(BIN, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)

LOADER_4802E0 = 0x4802e0
SELECTOR_4EC8C0 = 0x4ec8c0
FWD_492800 = 0x492800
PLAY_BOTTOM = 0x4015f0
PLAY_MAIN = 0x4997c0
SFX_TBL = 0x50ba40

# 扩展名 → 类别（依据本 EXE 实际用法 + NPK_SPEC / SNDATA_SPEC 既有结论）
EXT_CAT = {
    "LZW": "光荣 LS11 压缩资源（图像/数据/文本）",
    "GRP": "背景画/标题画（RGB565 裸图）",
    "PK8": "8bpp 画像（追加颜/外部颜）",
    "KOS": "效果音（KOS 音频）",
    "TR2": "剧本/数据档（SNDATA/BSDATA/SAVEDATA）",
    "DAT": "生数据（地物/坐标/表）",
    "IDX": "NPK 资源索引",
    "TMP": "运行时临时档（非发行物）",
    "SWP": "运行时交换档（非发行物）",
}


def rd(va, n):
    return MEM[va - BASE: va - BASE + n]


def cstr(va, maxlen=24):
    b = rd(va, maxlen)
    z = b.find(0)
    return b[:z if z >= 0 else maxlen].decode("ascii", "replace")


def imm_of(op_str):
    vals = []
    for tok in op_str.split(","):
        tok = tok.strip()
        if re.fullmatch(r"(0x[0-9a-f]+|[0-9]+)", tok):
            vals.append(int(tok, 16) if tok.startswith("0x") else int(tok))
    return vals


# ---------------- 1. 资源名扫描 ----------------
PAT = re.compile(rb"[A-F]:[A-Z0-9_]{1,12}\.[A-Z0-9]{2,3}")


def scan_resource_names():
    out = {}
    for m in PAT.finditer(MEM):
        e = m.end()
        if e >= len(MEM) or MEM[e] != 0:      # 必须以 NUL 结尾（真字符串）
            continue
        out[BASE + m.start()] = m.group().decode("ascii")
    return out


def cluster(addrs, gap=0x20):
    addrs = sorted(addrs)
    cl = []
    cur = [addrs[0]]
    for a in addrs[1:]:
        if a - cur[-1] <= gap:
            cur.append(a)
        else:
            cl.append(cur)
            cur = [a]
    cl.append(cur)
    return cl


# ---------------- 2. 调用点实参提取 ----------------
def find_call_sites(target):
    sites = []
    for off in range(len(MEM) - 5):
        if MEM[off] != 0xE8:
            continue
        rel = struct.unpack_from("<i", MEM, off + 1)[0]
        if ((BASE + off + 5 + rel) & 0xFFFFFFFF) != target:
            continue
        sites.append(BASE + off)
    return sites


def pushes_before(call_va, span=0x40):
    """枚举回溯长度，取指令边界对齐且窗口最大的那条，返回 push 立即数列表 [(va, val)]。"""
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


def raw_literal_refs(va):
    pat = struct.pack("<I", va)
    out = []
    off = 0
    while True:
        i = MEM.find(pat, off)
        if i < 0:
            break
        out.append(BASE + i)
        off = i + 1
    return out


# ---------------- 3. 原版文件对照 ----------------
def orig_files():
    names = set()
    if os.path.isdir(ORIG_DIR):
        for f in os.listdir(ORIG_DIR):
            if os.path.isfile(os.path.join(ORIG_DIR, f)):
                names.add(f)
    return names


# ---------------- 4. 自校验 ----------------
FAIL = []


def check(name, cond, extra=""):
    if not cond:
        FAIL.append(name)
    print("  [%s] %s%s" % ("OK  " if cond else "FAIL", name,
                           ("  -- " + extra) if extra and not cond else ""))


def main():
    print("=" * 78)
    print("太阁立志传2 · 原版资源/素材清单 参考实现自校验（续195）")
    print("=" * 78)

    names = scan_resource_names()
    addrs = sorted(names)
    print("\n[M1] 资源名扫描")
    check("M1-a 资源名总数 == 90", len(names) == 90, "got %d" % len(names))
    check("M1-b 全部形如 X:NAME.EXT（盘符 A-F）",
          all(re.fullmatch(r"[A-F]:[A-Z0-9_]+\.[A-Z0-9]{2,3}", s) for s in names.values()),
          str([s for s in names.values() if not re.fullmatch(r"[A-F]:[A-Z0-9_]+\.[A-Z0-9]{2,3}", s)]))

    groups = cluster(addrs)
    print("\n[M2] 阵列聚类（gap<=0x20）")
    check("M2 聚成 16 组", len(groups) == 16, "got %d" % len(groups))
    strides = Counter()
    for g in groups:
        for i in range(len(g) - 1):
            strides[g[i + 1] - g[i]] += 1
    check("M2-b 主阵列 stride 以 16B 为主", strides[16] >= 60, str(dict(strides)))
    for g in groups:
        print("        @0x%06x..0x%06x  n=%-2d  %s" % (
            g[0], g[-1], len(g), ", ".join(names[a][2:] for a in g[:6]) + ("..." if len(g) > 6 else "")))

    # ---- M3 加载点 ----
    print("\n[M3] 资源加载点（call 0x4802e0 / 0x4ec8c0 / 0x492800）")
    load_map = {}          # name_addr -> [(call_va, target_name)]
    n_sites = 0
    for tgt, tag in ((LOADER_4802E0, "0x4802e0"), (SELECTOR_4EC8C0, "0x4ec8c0"), (FWD_492800, "0x492800")):
        for va in find_call_sites(tgt):
            n_sites += 1
            for pa, pv in pushes_before(va):
                if pv in names:
                    load_map.setdefault(pv, []).append((va, tgt))
    covered = sorted(load_map)
    check("M3-a 加载类 call 站点 >= 40", n_sites >= 40, "got %d" % n_sites)
    check("M3-b 可归属到具体资源名的加载点 >= 40",
          sum(len(v) for v in load_map.values()) >= 40,
          "got %d" % sum(len(v) for v in load_map.values()))
    check("M3-c 有加载点的资源 >= 35 个", len(covered) >= 35, "got %d" % len(covered))
    print("        有加载点的资源 %d 个；示例：" % len(covered))
    for a in covered[:6]:
        print("          %-20s -> %s" % (names[a], ", ".join("0x%x" % v for v, _ in load_map[a][:3])))

    # ---- M4 音效表互证 ----
    print("\n[M4] 与音效子系统互证（sfx_subsystem_ref）")
    sfx_ptrs = [struct.unpack("<I", rd(SFX_TBL + 4 * i, 4))[0] for i in range(39)]
    check("M4-a 39 项音效指针全部命中已扫描资源名", all(p in names for p in sfx_ptrs),
          str([hex(p) for p in sfx_ptrs if p not in names][:3]))
    check("M4-b play_sfx(0x4997c0) 调用点 >= 70", len(find_call_sites(PLAY_MAIN)) >= 70,
          "got %d" % len(find_call_sites(PLAY_MAIN)))
    print("        音效子系统载入 %d 个 A:*.KOS（占全部资源 %d/%d）" % (39, 39, len(names)))

    # ---- M5 类别统计 ----
    print("\n[M5] 按扩展名分类")
    ext = Counter(names[a].rsplit(".", 1)[1] for a in addrs)
    for e, n in ext.most_common():
        print("        %-4s x%-3d %s" % (e, n, EXT_CAT.get(e, "?")))
    check("M5 扩展名全部在已知类别表内", all(e in EXT_CAT for e in ext), str(set(ext) - set(EXT_CAT)))

    # ---- M6 与原版文件对照 ----
    print("\n[M6] 与原版目录 Taikou2 Original/ 交叉对照")
    of = orig_files()
    of_up = {f.upper(): f for f in of}
    exe_names = {names[a][2:].upper() for a in addrs}      # 去盘符前缀
    missing = sorted(exe_names - set(of_up))               # EXE 引用但目录没有
    unused = sorted(f for u, f in of_up.items()
                    if u not in exe_names and re.fullmatch(r"[A-Z0-9_]+\.[A-Z0-9]{2,3}", u))
    check("M6-a 目录确实存在（>=100 个文件）", len(of) >= 100, "got %d" % len(of))
    runtime_tmp = sorted(m for m in missing if m.rsplit(".", 1)[1] in ("TMP", "SWP"))
    check("M6-b 运行时临时档（TMP/SWP）目录不收录属正常，且恰为 3 项",
          runtime_tmp == ["MIDI.TMP", "PVMM.SWP", "WAVE.TMP"], str(runtime_tmp))
    # 🆕 真发现：唯一「实质缺失」= B:MMLDATA.LZW（BGM/MML 序列数据）
    real_missing = sorted(set(missing) - set(runtime_tmp))
    check("M6-c 🆕 唯一实质缺失 = MMLDATA.LZW（BGM/MML 序列），中文版改用 MP3 目录替代",
          real_missing == ["MMLDATA.LZW"], str(real_missing))
    check("M6-d 佐证：目录含 MP3/ 与 mp3.dll（BGM 已改 MP3 方案）",
          os.path.isdir(os.path.join(ORIG_DIR, "MP3")) and os.path.exists(os.path.join(ORIG_DIR, "mp3.dll")))
    print("        EXE 引用但目录缺失 (%d): %s" % (len(missing), missing))
    print("         └ 运行时临时档 (正常): %s" % runtime_tmp)
    print("         └ 🆕 实质缺失 (BGM): %s  ← 中文版改用 MP3/ + mp3.dll" % real_missing)
    print("        目录有但 EXE 未引用 (%d): %s" % (len(unused), unused[:24]))

    # ---- M7 落盘 ----
    out = {
        "meta": {
            "title": "太阁立志传2 原版资源/素材清单（续195）",
            "total_resource_names": len(names),
            "groups": len(groups),
            "loader_4802e0": hex(LOADER_4802E0), "selector_4ec8c0": hex(SELECTOR_4EC8C0),
            "fwd_492800": hex(FWD_492800), "play_bottom_cdecl3": hex(PLAY_BOTTOM),
            "ext_category": EXT_CAT,
        },
        "resources": [
            {
                "name": names[a], "va": hex(a), "ext": names[a].rsplit(".", 1)[1],
                "category": EXT_CAT.get(names[a].rsplit(".", 1)[1], "?"),
                "group_base": hex(next(g[0] for g in groups if a in g)),
                "load_sites": ["0x%x(call 0x%x)" % (v, t) for v, t in load_map.get(a, [])],
                "literal_refs": ["0x%x" % r for r in raw_literal_refs(a)][:8],
            }
            for a in addrs
        ],
        "cross_check": {
            "orig_dir_files": len(of),
            "exe_referenced_but_missing": missing,
            "in_dir_but_not_referenced": unused,
        },
    }
    p = os.path.join(ROOT, "scripts", "resource_manifest.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n[输出] %s" % p)

    print("\n" + "=" * 78)
    if FAIL:
        print("RESULT: %d FAIL ❌ -> %s" % (len(FAIL), FAIL))
        return 1
    print("RESULT: ALL PASS ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
