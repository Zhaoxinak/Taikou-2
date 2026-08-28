#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_probe_exe.py — 太阁立志传2 TAIK2W95.exe 静态分析探针 (脱壳前基线)
=============================================================================

用途
----
在手工脱壳 (x32dbg + Scylla) 之前, 用纯标准库固化一份机器可读的 PE 静态快照:
  - 文件 SHA256 / 尺寸 (与 REVERSE_ENGINEERING.md §2.1 记录对比, 确认样本一致)
  - PE 头: machine / subsystem / 入口 RVA / ImageBase / 节对齐 / 数据目录
  - 节区表: 名称 / vsize / vaddr / rsize / roff / **熵** / 特征位 (含可执行判定)
  - 导入表: 每个 DLL 的 API 清单 (若 IAT 仍可静态解析)
  - 字符串: ASCII + UTF-16LE 可读串统计 + 关键词 (KOEI/KOS/LS11/...) 抽取
  - 加壳判定: 节名异常 / 代码节高熵 / 已知编译器/packer 特征串

脱壳后, 对 dump 再跑一次本脚本, diff 两份 JSON:
  - 若导入表从 null 变为非空, 且字符串里出现大量 GBK 菜单/错误提示 → 脱壳成功
  - 记录 OEP RVA / IAT 修复结果到文档 §2.1

依赖: 仅 Python 3 标准库 (struct / hashlib / math / json / os / sys / collections)
用法:
    python3 _probe_exe.py [EXE_PATH] [OUT_JSON]
    EXE_PATH 默认 F:/Games/Taikou2/TAIK2W95.exe
    OUT_JSON  默认 ./_probe_exe_baseline.json (相对脚本所在目录)
"""

import sys
import os
import json
import struct
import hashlib
import math
from collections import Counter

DEFAULT_EXE = r"F:/Games/Taikou2/TAIK2W95.exe"

# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def entropy(data):
    """香农熵 (字节分布), 范围 0..8。7.5+ 通常意味着压缩/加密。"""
    if not data:
        return 0.0
    n = len(data)
    counts = Counter(data)
    e = 0.0
    for v in counts.values():
        p = v / n
        e -= p * math.log2(p)
    return round(e, 4)


def cstr_at(b, off, limit=1024):
    """从 off 读取以 0 结尾的 ASCII 串 (C 风格)。"""
    if off is None or off < 0 or off >= len(b):
        return None
    end = b.find(b"\x00", off, off + limit)
    if end == -1:
        end = min(off + limit, len(b))
    s = b[off:end]
    # 必须全是可打印 ASCII 才当作有效串
    try:
        txt = s.decode("ascii")
    except UnicodeDecodeError:
        return None
    if not txt or any(ord(c) < 0x20 or ord(c) > 0x7E for c in txt):
        return None
    return txt


# ---------------------------------------------------------------------------
# RVA -> 文件偏移
# ---------------------------------------------------------------------------

def build_rva_map(sections):
    """返回把 RVA 映射到文件偏移的函数。
    sections: list of dict(name, vaddr, vsize, roff, rsize)
    规则: 落在某节 [vaddr, vaddr+max(vsize,rsize)) 内 → roff + (rva-vaddr);
          节之前 (RVA < 首节 vaddr) 视作头部, 偏移 == RVA。
    """
    secs = sorted(sections, key=lambda s: s["vaddr"])

    def rva_to_off(rva):
        if rva == 0:
            return None
        for s in secs:
            span = max(s["vsize"], s["rsize"])
            if s["vaddr"] <= rva < s["vaddr"] + span:
                return s["roff"] + (rva - s["vaddr"])
        if secs and rva < secs[0]["vaddr"]:
            return rva
        return None

    return rva_to_off


# ---------------------------------------------------------------------------
# PE 解析
# ---------------------------------------------------------------------------

SECTION_CHAR_FLAGS = {
    0x00000020: "CNT_CODE",
    0x00000040: "CNT_INIT_DATA",
    0x00000080: "CNT_UNINIT_DATA",
    0x02000000: "MEM_EXECUTE",
    0x04000000: "MEM_READ",
    0x08000000: "MEM_WRITE",
    0x10000000: "MEM_SHARED",
    0x80000000: "MEM_DISCARDABLE",
}

DATA_DIR_NAMES = [
    "export", "import", "resource", "exception", "security",
    "basereloc", "debug", "architecture", "globalptr", "tls",
    "load_config", "bound_import", "iat", "delay_import", "com_descriptor", "reserved",
]


def parse_pe(b):
    rep = {"valid": False, "notes": []}
    if b[:2] != b"MZ":
        rep["notes"].append("不是 MZ 文件")
        return rep, [], None
    (e_lfanew,) = struct.unpack_from("<I", b, 0x3C)
    if b[e_lfanew:e_lfanew + 4] != b"PE\x00\x00":
        rep["notes"].append(f"e_lfanew={e_lfanew:#x} 处无 PE 签名")
        return rep, [], None

    coff = e_lfanew + 4
    machine, num_sec, ts, ptr_sym, num_sym, opt_size, characteristics = struct.unpack_from("<HHIIIHH", b, coff)
    rep["machine"] = f"{machine:#06x}"
    rep["machine_name"] = {0x14c: "i386", 0x8664: "x86-64", 0x1c0: "ARM", 0xaa64: "ARM64"}.get(machine, "?")
    rep["num_sections"] = num_sec
    rep["timestamp"] = ts
    rep["characteristics"] = f"{characteristics:#06x}"
    rep["is_dll"] = bool(characteristics & 0x2000)

    opt = coff + 20
    (magic,) = struct.unpack_from("<H", b, opt)
    rep["pe_type"] = {0x10B: "PE32", 0x20B: "PE32+", 0x107: "ROM"}.get(magic, f"{magic:#x}")

    if magic == 0x10B:  # PE32 (本作是 32 位)
        (entry_rva,) = struct.unpack_from("<I", b, opt + 0x10)
        (image_base,) = struct.unpack_from("<I", b, opt + 0x1C)
        (section_align,) = struct.unpack_from("<I", b, opt + 0x20)
        (file_align,) = struct.unpack_from("<I", b, opt + 0x24)
        (subsystem,) = struct.unpack_from("<H", b, opt + 0x44)
        (dll_chars,) = struct.unpack_from("<H", b, opt + 0x46)
        (num_rva,) = struct.unpack_from("<I", b, opt + 0x5C)
    else:
        # PE32+ 路径 (本作不会走到, 但保留以防万一)
        (entry_rva,) = struct.unpack_from("<I", b, opt + 0x10)
        (image_base,) = struct.unpack_from("<Q", b, opt + 0x18)
        (section_align,) = struct.unpack_from("<I", b, opt + 0x20)
        (file_align,) = struct.unpack_from("<I", b, opt + 0x24)
        (subsystem,) = struct.unpack_from("<H", b, opt + 0x44)
        (dll_chars,) = struct.unpack_from("<H", b, opt + 0x46)
        (num_rva,) = struct.unpack_from("<I", b, opt + 0x5C)

    rep["entry_point_rva"] = f"{entry_rva:#010x}"
    rep["image_base"] = f"{image_base:#010x}"
    rep["section_alignment"] = section_align
    rep["file_alignment"] = file_align
    rep["subsystem"] = {1: "native", 2: "GUI", 3: "console"}.get(subsystem, f"{subsystem}")
    rep["dll_characteristics"] = f"{dll_chars:#06x}"

    # 数据目录
    dd_off = opt + 0x60
    data_dirs = {}
    for i in range(min(num_rva, len(DATA_DIR_NAMES))):
        va, size = struct.unpack_from("<II", b, dd_off + i * 8)
        data_dirs[DATA_DIR_NAMES[i]] = {"va": va, "size": size}
    rep["data_directories"] = data_dirs

    # 节区表 (紧跟可选头之后)
    sec_start = opt + opt_size
    sections = []
    for i in range(num_sec):
        base = sec_start + i * 40
        name_raw = b[base:base + 8]
        name = name_raw.split(b"\x00", 1)[0].decode("ascii", "replace")
        vsize, vaddr, rsize, roff = struct.unpack_from("<IIII", b, base + 8)
        chars = struct.unpack_from("<I", b, base + 36)[0]
        # 原始字节用于熵 (取 rsize 范围内存在的部分)
        raw = b[roff:roff + rsize] if 0 < rsize <= len(b) - roff else b""
        flags = [f for bit, f in SECTION_CHAR_FLAGS.items() if chars & bit]
        sections.append({
            "index": i,
            "name": name,
            "vsize": vsize,
            "vaddr": vaddr,
            "rsize": rsize,
            "roff": roff,
            "chars_hex": f"{chars:#010x}",
            "flags": flags,
            "is_exec": bool(chars & 0x02000000),
            "entropy": entropy(raw),
            "raw_len": len(raw),
        })

    rep["valid"] = True
    rep["notes"].append(f"解析成功: {num_sec} 节, {rep['pe_type']}")
    return rep, sections, data_dirs


# ---------------------------------------------------------------------------
# 导入表
# ---------------------------------------------------------------------------

def parse_imports(b, data_dirs, rva_to_off):
    imp = data_dirs.get("import")
    if not imp or imp["va"] == 0 or imp["size"] == 0:
        return None
    off = rva_to_off(imp["va"])
    if off is None:
        return None
    result = {}
    i = off
    while i + 20 <= len(b):
        oft, ts, fwd, name_rva, ft = struct.unpack_from("<IIIII", b, i)
        i += 20
        if oft == 0 and name_rva == 0 and ft == 0:
            break
        dll = cstr_at(b, rva_to_off(name_rva)) if name_rva else None
        if not dll:
            continue
        funcs = []
        thunk_rva = oft if oft != 0 else ft
        to = rva_to_off(thunk_rva)
        if to is not None:
            j = to
            while j + 4 <= len(b):
                (val,) = struct.unpack_from("<I", b, j)
                j += 4
                if val == 0:
                    break
                if val & 0x80000000:
                    funcs.append(f"#{val & 0x7FFFFFFF}")  # 按序号导入
                else:
                    no = rva_to_off(val)
                    if no is not None:
                        fn = cstr_at(b, no + 2)  # 跳过 2 字节 hint
                        if fn:
                            funcs.append(fn)
                        else:
                            funcs.append(f"?rva{val:08x}")
                    else:
                        funcs.append(f"?rva{val:08x}")
        result[dll] = funcs
    return result or None


# ---------------------------------------------------------------------------
# 字符串扫描
# ---------------------------------------------------------------------------

INTERESTING_KEYWORDS = [
    "KOEI", "TAIK", "KOS", "LS11", "MESSAGE", "TOWN", "BATTLE", "CASTLE",
    "SCENARIO", "MENU", "ERROR", "GAME", "CONFIG", "SAVE", "LOAD", ".TR2",
    ".LZW", ".GRP", ".BMP", "KAK", "GINOU", "BSDATA", "SNDATA", "VERSION",
]

KNOWN_COMPILER = [
    ("Microsoft Visual C++", [b"Microsoft Visual C++", b"MSVCRT", b"msvcrt.dll"]),
    ("Borland/CodeGear", [b"*", b"Borland"]),
    ("Visual Basic", [b"Visual Basic", b"vba"]),
    ("Watcom", [b"WATCOM", b"WCRT"]),
    ("Delphi", [b"Borland Delphi", b"Delphi"]),
    ("MinGW/GCC", [b"mingw", b"GCC:"]),
]


def scan_strings(b):
    summary = {"ascii_total": 0, "utf16_total": 0, "interesting": [], "interesting_set": []}
    # ASCII 连续可打印串
    buf = bytearray()
    ascii_runs = []
    for byte in b:
        if 0x20 <= byte <= 0x7E:
            buf.append(byte)
        else:
            if len(buf) >= 4:
                s = buf.decode("ascii")
                ascii_runs.append(s)
            buf = bytearray()
    if len(buf) >= 4:
        ascii_runs.append(buf.decode("ascii"))
    summary["ascii_total"] = len(ascii_runs)

    # UTF-16LE: 偶数字节为可打印 ASCII, 奇数字节为 0
    utf16_runs = []
    i = 0
    cur = []
    while i + 1 < len(b):
        lo, hi = b[i], b[i + 1]
        if hi == 0 and 0x20 <= lo <= 0x7E:
            cur.append(lo)
        else:
            if len(cur) >= 4:
                utf16_runs.append(bytes(cur).decode("ascii"))
            cur = []
        i += 2
    if len(cur) >= 4:
        utf16_runs.append(bytes(cur).decode("ascii"))
    summary["utf16_total"] = len(utf16_runs)

    # 关键词过滤 (ASCII + UTF16 合并)
    seen = set()
    for s in ascii_runs + utf16_runs:
        up = s.upper()
        for kw in INTERESTING_KEYWORDS:
            if kw in up and s not in seen:
                seen.add(s)
                summary["interesting"].append(s)
                break
    summary["interesting_set"] = sorted(seen)
    # 去重 interesting 列表
    summary["interesting"] = sorted(set(summary["interesting"]))
    return summary


def packer_hints(pe, sections, imports, strings):
    hints = []
    if sections:
        names = [s["name"] for s in sections]
        if "FuckALI" in names or any("Fuck" in n for n in names):
            hints.append("节名含 'FuckALI' / 'Fuck' 反逆向标记 → 典型保护器/混淆行为")
        for s in sections:
            if s["is_exec"] and s["entropy"] >= 7.0:
                hints.append(f"代码节 '{s['name']}' 熵={s['entropy']} ≥7.0 → 高度疑似压缩/加密代码")
            if s["is_exec"] and s["vsize"] > s["rsize"] * 2 and s["rsize"] > 0:
                hints.append(f"节 '{s['name']}' vsize({s['vsize']}) ≫ rsize({s['rsize']}) → 运行时解压")
    # 可静态解析的导入表?
    if imports:
        hints.append(f"导入表可静态解析: {len(imports)} 个 DLL, 共 {sum(len(v) for v in imports.values())} 个 API")
    else:
        hints.append("导入表无法静态解析 (IAT 或被加密/延迟绑定) → 加重'需动态脱壳'判定")
    # 编译器特征
    all_str = " ".join(strings["interesting"]).upper()
    blob = None
    return hints, all_str


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    exe = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_EXE
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "_probe_exe_baseline.json")

    if not os.path.isfile(exe):
        print(f"[ERR] 找不到 EXE: {exe}")
        sys.exit(2)

    with open(exe, "rb") as f:
        b = f.read()

    file_info = {
        "path": os.path.abspath(exe),
        "size": len(b),
        "sha256": sha256_file(exe),
        "mtime": os.path.getmtime(exe),
    }

    pe, sections, data_dirs = parse_pe(b)
    rva_to_off = build_rva_map(sections)
    imports = parse_imports(b, data_dirs, rva_to_off) if pe.get("valid") else None
    strings = scan_strings(b)
    hints, _ = packer_hints(pe, sections, imports, strings)

    report = {
        "file": file_info,
        "pe": pe,
        "sections": sections,
        "imports": imports,
        "strings_summary": {
            "ascii_total": strings["ascii_total"],
            "utf16_total": strings["utf16_total"],
            "interesting_count": len(strings["interesting"]),
            "interesting_sample": strings["interesting"][:200],
        },
        "packer_hints": hints,
    }

    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # ---- 人类可读摘要 ----
    print("=" * 70)
    print(f"EXE 静态探针: {file_info['path']}")
    print("=" * 70)
    print(f"尺寸        : {file_info['size']:,} B")
    print(f"SHA256     : {file_info['sha256']}")
    print(f"PE 类型    : {pe.get('pe_type')}  machine={pe.get('machine')}({pe.get('machine_name')})")
    print(f"子系统     : {pe.get('subsystem')}  入口RVA={pe.get('entry_point_rva')}  ImageBase={pe.get('image_base')}")
    print(f"节对齐/文件 : {pe.get('section_alignment')} / {pe.get('file_alignment')}")
    print("-" * 70)
    print("节区表:")
    print(f"  {'#':>2} {'name':<10} {'vsize':>10} {'vaddr':>10} {'rsize':>10} {'roff':>10} {'熵':>6} flags")
    for s in sections:
        print(f"  {s['index']:>2} {s['name']:<10} {s['vsize']:>10} {s['vaddr']:>#10x} {s['rsize']:>10} {s['roff']:>#10x} {s['entropy']:>6} {','.join(s['flags'])}")
    print("-" * 70)
    if imports:
        print(f"导入表: {len(imports)} 个 DLL")
        for dll, funcs in imports.items():
            print(f"  {dll}: {len(funcs)} APIs  e.g. {', '.join(funcs[:8])}")
    else:
        print("导入表: 无法静态解析 (null / 加密)")
    print("-" * 70)
    print(f"字符串: ASCII={strings['ascii_total']}  UTF16={strings['utf16_total']}  关键词命中={len(strings['interesting'])}")
    if strings["interesting"]:
        print("  关键词样本: " + " | ".join(strings["interesting"][:30]))
    print("-" * 70)
    print("加壳/混淆判定:")
    for h in hints:
        print(f"  * {h}")
    print("=" * 70)
    print(f"基线 JSON 已写入: {out}")


if __name__ == "__main__":
    main()
