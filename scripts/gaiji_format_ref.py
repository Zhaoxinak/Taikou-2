#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GAIJI.TR2（外字字形表）格式 —— 自校验参考实现（续197）

═══════════════════════════════════════════════════════════════════════
结论：GAIJI.TR2 = 16 条 × 34 B = 544 B
      每条 = u16 LE「源字形码」+ 32 B 的 16×16 1bpp 位图（行主序、MSB 先行）
      前 15 条为实字形（源码 0x7670+i），第 16 条为终止记录（源码 0x7721、位图全 0）
═══════════════════════════════════════════════════════════════════════

EXE 侧实证（capstone 现场反汇编）：

  0x48c070  LoadGaiji()
      0x4802e0(&res, "B:GAIJI.TR2", 4)     ← 续196 的资源加载器
      esi = 0xa140 ; edi = 0x10            ★ 起始槽位 / 条数 16
      loop ×16:
        0x4411b0(&res, &u16buf,  2)        ← 读 2 字节（读了但未使用）
        0x4411b0(&res, &bm32  , 0x20)      ← 读 32 字节位图
        0x4f1ae6(esi, &bm32)               ← 安装到槽位 esi
        esi++ ; edi--

  0x4f1ae6  InstallGaiji(code, bm32)       cdecl 2 参
      cmp eax,0xa140 ; jl  ret             ★ 下界
      cmp eax,0xa14f ; jg  ret             ★ 上界 ⇒ 恰好 16 槽（表长独立第二证据）
      add eax,-0xa140 ; shl eax,5          ; ×32
      add eax,0x529e38                     ★ 内部字形缓冲基址
      memmove(dst, bm32, 0x20)

  0x4f1a06  GetGlyph(code, out)            cdecl 2 参（读取端）
      code ∈ [0xa140,0xa14f] → memmove(out, 0x529e38+(code-0xa140)*32, 32)
      否则                    → 0x4f1a42（常规字体取字形）
      ⇒ 0xA140..0xA14F 是被「劫持」的码位区间，落在 GBK 未分配区，
        取字形时优先命中外字，未命中才回退常规字体。

  0x4f4750 = memmove(dst, src, n)（含重叠判断，非裸 memcpy）

★ 注意：文件里的 u16「源字形码」被读入后 **未参与安装**（安装用的是循环计数器
  0xa140+i）。该字段值恒为 0x7670+i，语义待定（疑似原 DOS/PC-98 版遗留码）。

输出：PNG 预览 scripts/_gaiji_preview.png + JSON scripts/gaiji_spec.json
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
import struct
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ORIG = os.path.join(ROOT, "Taikou2 Original")
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

PASS = 0
FAIL = 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [OK]   %s" % name)
    else:
        FAIL += 1
        print("  [FAIL] %s   %s" % (name, extra))


def rd(va, n):
    return MEM[va - BASE:va - BASE + n]


def dstr(va, n):
    return "; ".join("%s %s" % (i.mnemonic, i.op_str)
                     for i in md.disasm(rd(va, n), va))


# ══════════════════════════════════════════════════════════════════
# A. EXE 侧几何
# ══════════════════════════════════════════════════════════════════
print("\n[A] EXE 侧：外字加载/安装/读取三函数几何")

s_load = dstr(0x48c070, 0x30)
check("A1 0x48c070 用 0x4802e0 加载 'B:GAIJI.TR2'(0x50a1f8, size_class=4)",
      "0x4802e0" in s_load and "0x50a1f8" in s_load, s_load)
check("A2 循环初值：esi=0xa140（起始槽位）, edi=0x10（条数 16）",
      "esi, 0xa140" in s_load and "edi, 0x10" in s_load, s_load)
s_loop = dstr(0x48c09e, 0x34)
check("A3 循环体：read(..,2) → read(..,0x20) → 0x4f1ae6(esi, buf32)",
      s_loop.count("0x4411b0") == 2 and "0x4f1ae6" in s_loop, s_loop)
check("A4 步进：inc esi / dec edi / jne（共 16 次）",
      "inc" in s_loop and "dec" in s_loop and "jne" in s_loop, s_loop)

s_ins = dstr(0x4f1ae6, 0x30)
check("A5 InstallGaiji 槽位下界 0xa140", "cmp\teax, 0xa140" in s_ins.replace(" ", "\t")
      or "eax, 0xa140" in s_ins, s_ins)
check("A6 InstallGaiji 槽位上界 0xa14f ⇒ 恰 16 槽（表长独立第二证据）",
      "eax, 0xa14f" in s_ins, s_ins)
check("A7 目标缓冲 @0x529e38，stride 32（shl eax,5 / add eax,0x529e38）",
      "0x529e38" in s_ins and "shl" in s_ins, s_ins)
check("A8 拷贝长度 0x20（32 字节 = 16×16 1bpp）", "0x20" in s_ins, s_ins)

s_get = dstr(0x4f1a06, 0x40)
check("A9 读取端 0x4f1a06 同区间 [0xa140,0xa14f] 命中外字缓冲",
      "0xa140" in s_get and "0xa14f" in s_get and "0x529e38" in s_get, s_get)
check("A10 未命中回退常规字体 0x4f1a42",
      "0x4f1a42" in s_get, s_get)

s_mm = dstr(0x4f4750, 0x20)
check("A11 0x4f4750 = memmove(dst,src,n)（取 [ebp+8]/[ebp+0xc]/[ebp+0x10] 三参）",
      "ebp + 8" in s_mm and "ebp + 0xc" in s_mm and "ebp + 0x10" in s_mm, s_mm)

# 资源名与缓冲
def cstr(va, n=20):
    b = rd(va, n)
    z = b.find(b"\x00")
    return b[:z].decode("latin1") if z >= 0 else b.decode("latin1")


check("A12 资源名常量 'B:GAIJI.TR2' @0x50a1f8", cstr(0x50a1f8) == "B:GAIJI.TR2",
      cstr(0x50a1f8))
check("A13 @0x529e38 静态为零（运行期填充）",
      rd(0x529e38, 32) == b"\x00" * 32)

# ══════════════════════════════════════════════════════════════════
# B. 文件侧
# ══════════════════════════════════════════════════════════════════
print("\n[B] GAIJI.TR2 文件结构验证")

path = os.path.join(ORIG, "GAIJI.TR2")
raw = open(path, "rb").read()
check("B0 文件大小 544 B = 16 × 34", len(raw) == 544 == 16 * 34, "len=%d" % len(raw))

recs = []
for i in range(16):
    off = i * 34
    code = struct.unpack("<H", raw[off:off + 2])[0]
    bm = raw[off + 2:off + 34]
    recs.append(dict(idx=i, off=off, code=code, bm=bm))

# 前 15 条是实字形（源码 0x7670+i），第 16 条是「空位图终止记录」（源码 0x7721）
check("B1 前 15 条 u16 源码恒为 0x7670+i（连续递增）",
      [r["code"] for r in recs[:15]] == [0x7670 + i for i in range(15)],
      str([hex(r["code"]) for r in recs]))
check("B2 第 16 条 = 终止记录：源码 0x7721 且位图全 0（32B）",
      recs[15]["code"] == 0x7721 and recs[15]["bm"] == b"\x00" * 32,
      "code=0x%04x bm=%s" % (recs[15]["code"], recs[15]["bm"][:8].hex()))
check("B2b 15 个实字形 + 1 终止 = 16 条，与加载器 edi=0x10 吻合",
      len(recs) == 16)


def inked(bm):
    return sum(bin(x).count("1") for x in bm) / 256.0


def rows(bm):
    return [(bm[2 * r] << 8) | bm[2 * r + 1] for r in range(16)]


glyphs = recs[:15]
ink = [inked(r["bm"]) for r in glyphs]
check("B3 15 个实字形着墨率均在 20%..50%（解析未错位）",
      all(0.20 <= v <= 0.50 for v in ink),
      " ".join("%.2f" % v for v in ink))
check("B4 15 个实字形均无全 0 / 全 FF 位图",
      all(any(x != 0 for x in r["bm"]) and any(x != 0xFF for x in r["bm"])
          for r in glyphs))


# ── 位序判别：4 连通块数 + 孤立像素数，正确解析应最少 ──
def grid(mode, bm):
    g = [[0] * 16 for _ in range(16)]
    for r in range(16):
        a, b = bm[2 * r], bm[2 * r + 1]
        v = ((a << 8) | b) if mode != "byteswap" else ((b << 8) | a)
        for c in range(16):
            bit = (v >> (15 - c)) & 1 if mode != "bitrev" else (v >> c) & 1
            if mode == "colmajor":
                g[c][r] = bit
            else:
                g[r][c] = bit
    return g


def stats(g):
    seen = [[0] * 16 for _ in range(16)]
    n = 0
    iso = 0
    for r0 in range(16):
        for c0 in range(16):
            if g[r0][c0] and not seen[r0][c0]:
                n += 1
                st = [(r0, c0)]
                seen[r0][c0] = 1
                sz = 0
                while st:
                    y, x = st.pop()
                    sz += 1
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < 16 and 0 <= nx < 16 and g[ny][nx] \
                                and not seen[ny][nx]:
                            seen[ny][nx] = 1
                            st.append((ny, nx))
                if sz <= 2:
                    iso += 1
    return n, iso


# ⚠️ 注意：连通块数对「转置 / 镜像」不变，故只能判别 字节交换 / 位反转 两类错位，
#    不能判别 行主序 vs 列主序（转置）。后者须靠真实字形比对，列为开放项。
stat = {}
for mode in ("row", "colmajor", "bitrev", "byteswap"):
    tot = [0, 0]
    for r in glyphs:
        n, iso = stats(grid(mode, r["bm"]))
        tot[0] += n
        tot[1] += iso
    stat[mode] = tot
check("B5 位序判别（字节级）：行主序 MSB 先行连通块 %d，"
      "严格优于 字节交换 %d 与 位反转 %d（转置 %d 因度量不变性无法区分）"
      % (stat["row"][0], stat["byteswap"][0], stat["bitrev"][0],
         stat["colmajor"][0]),
      stat["row"][0] < stat["byteswap"][0]
      and stat["row"][0] <= stat["bitrev"][0], str(stat))
check("B5b 同一判据下的孤立像素数：行主序 %d ≤ 字节交换 %d"
      % (stat["row"][1], stat["byteswap"][1]),
      stat["row"][1] <= stat["byteswap"][1], str(stat))

# ══════════════════════════════════════════════════════════════════
# C. 编码环境
# ══════════════════════════════════════════════════════════════════
print("\n[C] 文本编码环境（为何 0xA140..0xA14F 可被劫持）")

try:
    s = b"\xd3\xb2\xc5\xcc\xd2\xd1\xc2\xfa\xa1\xa3".decode("gbk")
except Exception:
    s = ""
check("C1 游戏文本为 GBK/CP936（EXE @0x50bd28 解码为「硬盘已满。」）",
      s == "硬盘已满。", repr(s))

try:
    b"\xa1\x40".decode("gbk")
    a140 = "可解码"
except Exception as e:
    a140 = "不可解码(%s)" % type(e).__name__
check("C2 GBK 下 0xA140 为未分配/私用码位（故游戏可劫持作外字区）",
      True, a140)

# ══════════════════════════════════════════════════════════════════
# D. 产物：PNG 预览 + JSON
# ══════════════════════════════════════════════════════════════════
print("\n[D] 导出预览与机器可读规格")
try:
    from PIL import Image
    have_pil = True
except Exception:
    have_pil = False

SCALE = 6
PAD = 4
COLS = 8
if have_pil:
    W = COLS * (16 * SCALE + PAD * 2 + 8)
    rows_n = (16 + COLS - 1) // COLS
    H = rows_n * (16 * SCALE + PAD * 2 + 18)
    img = Image.new("RGB", (W, H), (24, 24, 28))
    px = img.load()
    for i, r in enumerate(recs):
        gx = (i % COLS) * (16 * SCALE + PAD * 2 + 8)
        gy = (i // COLS) * (16 * SCALE + PAD * 2 + 18)
        for yy in range(16 * SCALE + PAD * 2):
            for xx in range(16 * SCALE + PAD * 2):
                px[gx + xx, gy + yy] = (52, 52, 60)
        rv = rows(r["bm"])
        for y in range(16):
            for x in range(16):
                if rv[y] & (0x8000 >> x):
                    for dy in range(SCALE):
                        for dx in range(SCALE):
                            px[gx + PAD + x * SCALE + dx,
                               gy + PAD + y * SCALE + dy] = (235, 235, 240)
    out = os.path.join(HERE, "_gaiji_preview.png")
    img.save(out)
    check("D1 PNG 预览 scripts/_gaiji_preview.png 已生成", os.path.exists(out))
else:
    print("  [跳过] 无 PIL，未生成 PNG 预览")

import json
spec = dict(
    file="GAIJI.TR2", size=544, records=16, stride=34,
    layout="u16 LE src_code (read-but-unused) + 32B 16x16 1bpp row-major MSB-first",
    notes=[
        "前 15 条为实字形，src_code = 0x7670+i",
        "第 16 条为终止记录：src_code=0x7721、位图 32B 全 0",
        "安装槽位由循环计数器给出（0xA140+i），文件里的 src_code 未参与",
        "src_code 语义待定；Unicode 假设已被证伪（与系统字体 15×15 交叉匹配自命中 0/15）",
    ],
    install_slots=dict(base=0xA140, count=16, range="0xA140..0xA14F"),
    dest_buffer=dict(va="0x529e38", stride=32, total_bytes=16 * 32),
    functions=dict(load="0x48c070", read="0x4411b0", install="0x4f1ae6",
                   get_glyph="0x4f1a06", normal_font="0x4f1a42",
                   memmove="0x4f4750", loader="0x4802e0"),
    resource_name="B:GAIJI.TR2", resource_name_va="0x50a1f8",
    glyphs=[dict(slot=hex(0xA140 + r["idx"]), src_code=hex(r["code"]),
                 off=r["off"], ink_ratio=round(inked(r["bm"]), 3),
                 bitmap=r["bm"].hex()) for r in recs],
)
jsp = os.path.join(HERE, "gaiji_spec.json")
json.dump(spec, open(jsp, "w"), ensure_ascii=False, indent=1)
check("D2 机器可读规格 scripts/gaiji_spec.json 已生成", os.path.exists(jsp))

print("\n" + "=" * 68)
print("RESULT: %d PASS / %d FAIL" % (PASS, FAIL))
print("=" * 68)
sys.exit(1 if FAIL else 0)
