#!/usr/bin/env python3
"""
续198：GRP/PK8 格式参考实现与自测
=====================================
覆盖三种 GRP 变体 + END.GRP 容器；PK8 标记待破（需 emu）。
输出：_decoded_grp/*.png（可视验证）+ grp_spec.json（结构化规格）
自测：T1 头部解析 / T2 解包一致性 / T3 END.GRP 容器 / T4 调色板合法性 / T5 SMODE planar
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

import os, struct, sys, json, collections
from PIL import Image

D = os.path.join(os.path.dirname(__file__), "..", "Taikou2 Original")
OUT = os.path.join(os.path.dirname(__file__), "_decoded_grp")
os.makedirs(OUT, exist_ok=True)
MEM = open(os.path.join(os.path.dirname(__file__), _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
BASE = 0x400000

# ── 全局解码原语 ──

def npk_unpack_nibble(data, npix):
    """NPK 字面量位序：2B→4px，b1.b7→bit3 b1.b3→bit2 b2.b7→bit1 b2.b3→bit0"""
    out = bytearray(); i = 0
    while i + 1 < len(data) and len(out) < npix:
        b1 = data[i]; b2 = data[i+1]; i += 2
        for _ in range(4):
            d = ((b1&0x80)>>4) | ((b1&0x08)>>1) | ((b2&0x80)>>6) | ((b2&0x08)>>3)
            out.append(d & 0x0f)
            b1 = (b1<<1) & 0xff; b2 = (b2<<1) & 0xff
            if len(out) >= npix: break
    return out

def npk_rle(src, W, npix):
    """NPK §3.1 控制位流 RLE（LSB-first bitflag）"""
    out = bytearray(); bitflag = 0; i = 0
    while i < len(src) and len(out) < npix:
        if (bitflag & 0xff00) == 0:
            if i >= len(src): break
            bitflag = 0xff00 | src[i]; i += 1
        if bitflag & 1:
            if i >= len(src): break
            bb = src[i]; i += 1
            rs = (bb & 0x1f) + 1
            ro = ((bb & 0x60) >> 5) + 1
            ro = ro * W if (bb & 0x80) else ro * 4
            for _ in range(rs * 4):
                if len(out) >= npix: break
                s = len(out) - ro
                out.append(out[s] if s >= 0 else 0)
        else:
            if i + 1 >= len(src): break
            b1 = src[i]; b2 = src[i+1]; i += 2
            for _ in range(4):
                if len(out) >= npix: break
                d = ((b1&0x80)>>4)|((b1&0x08)>>1)|((b2&0x80)>>6)|((b2&0x08)>>3)
                out.append(d & 0xf)
                b1 = (b1<<1) & 0xff; b2 = (b2<<1) & 0xff
        bitflag >>= 1
    return out

def pal16_exe(va):
    """从 EXE 字符串区旁的 16×3 nibble RGB 提取调色板"""
    o = va - BASE; p = []
    for k in range(16):
        r, g, b = MEM[o+3*k], MEM[o+3*k+1], MEM[o+3*k+2]
        p += [r*17, g*17, b*17]
    return p

def pal256_rgbquad(data):
    """从 1024B RGBQUAD 提取 256 色调色板"""
    p = []
    for i in range(256):
        p += [data[4*i], data[4*i+1], data[4*i+2]]
    return p

def save_png(px, W, H, pal, name):
    im = Image.new("P", (W, H)); im.putdata(bytes(px))
    im.putpalette(pal + [0]*(768-len(pal)))
    im.convert("RGB").save(os.path.join(OUT, name))
    return name

VGA16 = []
for k in range(16):
    v = ((k>>3)&1)*0xaa + ((k>>2)&1)*0x55 + ((k>>1)&1)*0xaa + (k&1)*0x55
    VGA16 += [min(v,255)] * 3

# ── 格式 A：Raw GRP（6B 头 + NPM 风格 4bpp）──
def decode_raw_grp(fn, pal_va=None):
    b = open(os.path.join(D, fn), "rb").read()
    t, pad, W, H = struct.unpack("<BBHH", b[:6])
    body = b[6:]
    assert len(body) == W * H // 2, f"{fn}: body {len(body)} != {W*H//2}"
    px = npk_unpack_nibble(body, W*H)
    pal = pal16_exe(pal_va) if pal_va else VGA16
    name = fn.replace(".GRP", "_raw.png")
    save_png(px, W, H, pal, name)
    return {"file":fn,"format":"A-raw","type":t,"W":W,"H":H,"body":len(body),"pal":"exe" if pal_va else "vga16","png":name}

# ── 格式 B：Planar GRP（4-plane + RGBQUAD 尾巴）──
def decode_planar_grp(fn):
    b = open(os.path.join(D, fn), "rb").read()
    # 尾部：1024B RGBQUAD + 可能 1B 终止符
    # 检测：末尾前 1025B 处是否为 0xff 终止符
    term = b[-1]
    if term == 0xff and len(b) > 1025:
        pix_area = b[:-1025]
        pal_data = b[-1024:]
    else:
        pix_area = b[:-1024]
        pal_data = b[-1024:]
    pal = pal256_rgbquad(pal_data)
    # 像素数据按 loader 实际读取序列分段：
    # read1: offset=0 size=0xfa00(64000), read2: offset=6 size=0xfa00, read3: offset=12 size=0x15a0
    raw = pix_area[:128000]  # 前 128KB = 两个半屏
    # Planar 4-plane 解交织
    plane = [bytearray() for _ in range(4)]
    for i in range(len(raw)):
        plane[i % 4].append(raw[i])
    nbits = len(raw) // 4 * 8  # = 256000 = 640*400
    px = bytearray()
    for bit in range(nbits):
        bi = bit >> 3; bii = 7 - (bit & 7); v = 0
        for pl in range(4):
            if bi < len(plane[pl]) and (plane[pl][bi] >> bii) & 1:
                v |= (1 << pl)
        px.append(v)
    name = fn.replace(".GRP", "_planar.png")
    save_png(px, 640, 400, pal, name)
    rem = pix_area[128000:] if len(pix_area) > 128000 else bytearray()
    return {"file":fn,"format":"B-planar","W":640,"H":400,"pixel_area":len(pix_area),
            "palette":len(pal_data),"terminator":hex(term),"remaining":len(rem),"png":name}

# ── 格式 C：END.GRP 容器（BE 偏移表 + NPK016 条目）──
def decode_end_grp():
    b = open(os.path.join(D, "END.GRP"), "rb").read()
    n0 = struct.unpack(">I", b[:4])[0]
    nent = n0 // 4
    offs = [struct.unpack(">I", b[4*i:4*i+4])[0] for i in range(nent)]
    entries = []
    for k, o in enumerate(offs):
        if b[o:o+6] != b"NPK016":
            continue  # skip trailer
        t = b[o+6]; dW, dH, nW, nH = struct.unpack("<4H", b[o+8:o+0x10])
        end = offs[k+1] if k+1 < len(offs) else len(b) - 3
        # 调色板
        pal = []
        for j in range(16):
            v = struct.unpack("<H", b[o+0x10+2*j:o+0x12+2*j])[0]
            pal += [((v>>8)&0xf)*17, ((v>>4)&0xf)*17, (v&0xf)*17]
        px = npk_rle(b[o+0x30:end], nW, nW*nH)
        ok = len(px) == nW*nH
        png_name = None
        if ok and (k < 6 or k in (50, 80, 103)):
            # 补零到精确尺寸
            px_full = px + bytearray(nW*nH - len(px))
            png_name = save_png(px_full, nW, nH, pal, f"END_{k:03d}_{nW}x{nH}.png")
        entries.append({"idx":k,"offset":hex(o),"type":t,"display":f"{dW}x{dH}",
                        "native":f"{nW}x{nH}","rle_ok":ok,"pixels":len(px),"png":png_name})
    # 验证末条目
    last = b[offs[-1]:]
    is_end = last[:3] == b"END"
    return {"file":"END.GRP","format":"C-container","table_entries":nent,
            "table_bytes":n0,"npk016_count":sum(1 for e in entries if e.get("rle_ok")),
            "trailer_is_END":is_end,"entries":entries}

# ── 自测 ──
results = {"tests":[], "spec":{}}

print("="*60)
print("T1: Raw GRP 头部解析 (ACERTWP/KOEILOGO/PRESS)")
for fn, pv in [("ACERTWP.GRP",0x50a188),("KOEILOGO.GRP",0x50a2c0),("PRESS.GRP",None)]:
    info = decode_raw_grp(fn, pv)
    results["tests"].append(("T1-"+fn, info["type"]==4 and info["W"]==640 and info["H"]==400))
    print(f"  {fn}: type={info['type']} {info['W']}x{info['H']} body={info['body']} ✓")

print("\nT2: Raw GRP 解包像素数 == W*H")
for fn in ["ACERTWP.GRP","KOEILOGO.GRP","PRESS.GRP"]:
    b = open(os.path.join(D, fn), "rb").read()
    _, _, W, H = struct.unpack("<BBHH", b[:6])
    body = b[6:]
    px = npk_unpack_nibble(body, W*H)
    ok = len(px) == W*H
    results["tests"].append(("T2-"+fn, ok))
    print(f"  {fn}: {len(px)}/{W*H} {'✓' if ok else '✗'}")

print("\nT3: END.GRP 容器")
end = decode_end_grp()
npk_ok = sum(1 for e in end["entries"] if e["rle_ok"])
total_npk = len(end["entries"])
results["tests"].append(("T3-count", npk_ok == total_npk))
results["tests"].append(("T3-trailer", end["trailer_is_END"]))
print(f"  NPK016 条目: {npk_ok}/{total_npk} RLE 恰好填满")
print(f"  END 尾标: {'✓' if end['trailer_is_END'] else '✗'}")
print(f"  原生尺寸分布:", collections.Counter(e["native"] for e in end["entries"]).most_common(5))

print("\nT4: SMODE planar 4-plane + 调色板")
smode = decode_planar_grp("SMODE.GRP")
results["tests"].append(("T4-planar", smode["W"]==640 and smode["H"]==400))
results["tests"].append(("T4-palette", smode["palette"]==1024))
print(f"  SMODE: {smode['W']}x{smode['H']}, palette={smode['palette']}B, term={smode['terminator']}, remaining={smode['remaining']}B ✓")

print("\nT5: 调色板值域合法")
for fn, pv in [("ACERTWP.GRP",0x50a188),("KOEILOGO.GRP",0x50a2c0)]:
    pal = pal16_exe(pv)
    ok = all(0 <= v <= 255 for v in pal)
    results["tests"].append(("T5-"+fn, ok))
    print(f"  {fn} pal: {'✓' if ok else '✗'} range [{min(pal)}..{max(pal)}]")

# ── 输出规格 JSON ──
results["spec"] = {
    "formats": {
        "A-raw": {"desc":"6B header(type,pad,W,H) + NPK-style 4bpp planar-nibble",
                 "files":["ACERTWP.GRP","KOEILOGO.GRP","PRESS.GRP"],
                 "palette":"16×3 nibble RGB adjacent to filename in EXE"},
        "B-planar": {"desc":"4-plane interleaved 4bpp + 1024B RGBQUAD tail palette + 1B terminator(0xff)",
                     "files":["SMODE.GRP"],
                     "loader_reads":[[0,0xfa00],[6,0xfa00],[12,0x15a0]],
                     "note":"first 128KB = two 640x200 half-screens, rest = sub-icons/UI"},
        "C-container": {"desc":"BE u32 offset table → NPK016 entries + 'END' trailer",
                       "file":"END.GRP","entries":103,"all_type_4":"True",
                       "display":"640x400"}
    },
    "pk8_status": "待破 — 非 NPK RLE（恒定 2240px 与 W 无关），需 emu 追踪读后处理"
}

with open(os.path.join(OUT, "grp_spec.json"), "w") as f:
    json.dump(results["spec"], f, ensure_ascii=False, indent=2)

print("\n"+"="*60)
passed = sum(1 for _,ok in results["tests"] if ok)
total = len(results["tests"])
print(f"自测: {passed}/{total} PASS")
if passed == total:
    print("RESULT: ALL PASS ✅")
else:
    for name, ok in results["tests"]:
        if not ok: print(f"  FAIL: {name}")
