#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KOS / KOB 音频容器格式 —— 自校验参考实现（续197）

═══════════════════════════════════════════════════════════════════════
结论：KOS = 「1 字节 XOR 密钥 + 标准 RIFF/WAVE」
═══════════════════════════════════════════════════════════════════════

  offset 0        : u8   XOR 密钥 key（本作全部 39 个文件均为 0xAE）
  offset 1 .. EOF : 标准 WAV，逐字节 XOR key

EXE 侧实现（静态反汇编实证，主函数 0x4993a0）：

  0x499380  xor16(buf, key16, len)          cdecl 3 参
      mov ecx,[esp+0xc]   ; len
      mov eax,[esp+4]     ; buf
      test ecx,ecx ; jbe ret
      mov dx,[esp+8]      ; key16
      inc ecx ; shr ecx,1 ; ecx = ceil(len/2)
    @@:xor word[eax],dx  ; ★ 16 位为单位
      add eax,2 ; dec ecx ; jne @b
      ret

  0x4993a0  load_and_decode_sound(name)：
      0x499360(name, '.')         = strchr  → 扩展名指针
      0x4f43f0(ext, ".KOB") 命中 → 目标 "A:MIDI.TMP"
      0x4f43f0(ext, ".KOS") 命中 → 目标 "A:WAVE.TMP"
      其它扩展名                → 不解码，直接用原名
      0x4ec8c0(&res, name, 4)     ← 续196 的资源加载器（size_class=4）
      0x4ec960(&res)              → esi = 数据长度（= filesize-1，密钥字节已消耗）
      0x4ec9a0(&res)              → eax = 第 0 字节 = key
      0x4994ea mov dh,bl           ; dh = key
      0x4994f4 or  ebx,edx         ; ebx = key | key<<8  ★ 单字节扩展成 key16
      分块（块长 [0x524904]-1，默认 255）循环 xor16 → 写到 TMP

★ 关键点：key 是「从文件里读出来的」，不是硬编码立即数。
  这解释了为什么全镜像扫 `xor ..., 0xae` 立即数 0 命中 —— 密钥来自数据。

本脚本自校验 + 全量解码输出到 scripts/_decoded_kos/*.wav
"""
import os
import re
import struct
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ORIG = os.path.join(ROOT, "Taikou2 Original")
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
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


def disasm(va, n):
    return list(md.disasm(rd(va, n), va))


def dstr(va, n):
    return "; ".join("%s %s" % (i.mnemonic, i.op_str) for i in disasm(va, n))


# ══════════════════════════════════════════════════════════════════
# A. EXE 侧：解码器几何
# ══════════════════════════════════════════════════════════════════
print("\n[A] EXE 侧解码器几何（capstone 现场反汇编）")

s = dstr(0x499380, 0x20)
check("A1 0x499380 = xor16(buf,key16,len)：mov ecx,[esp+0xc] / mov eax,[esp+4]",
      "esp + 0xc" in s and "esp + 4" in s, s)
check("A2 取 16 位密钥：mov dx, word [esp + 8]",
      "dx, word ptr [esp + 8]" in s, s)
check("A3 循环体 = xor word [eax], dx  + add eax,2（16 位步进）",
      "xor\tword ptr [eax], dx" in s.replace("  ", " ").replace(" ", "\t")
      or "xor word ptr [eax], dx" in s, s)
check("A4 计数 = (len+1)>>1：inc ecx / shr ecx,1",
      "inc" in s and "shr" in s, s)
check("A5 cdecl 3 参、普通 ret（调用方清栈，见 0x499571 add esp,0xc）",
      any(i.mnemonic == "ret" and i.op_str == "" for i in disasm(0x499380, 0x20)))

# 密钥扩展：mov dh,bl ; or ebx,edx
s2 = dstr(0x4994e6, 0x10)
check("A6 单字节密钥扩展成 16 位：mov dh,bl ... or ebx,edx（key16 = key|key<<8）",
      "dh, bl" in s2 and "ebx, edx" in s2, s2)

# 分派：.KOB / .KOS / 其它
def cstr(va, n=16):
    b = rd(va, n)
    z = b.find(b"\x00")
    return b[:z].decode("latin1") if z >= 0 else b.decode("latin1")


check("A7 扩展名分派常量：'.KOS' → A:WAVE.TMP",
      cstr(0x50bd68) == ".KOS" and cstr(0x50bd5c) == "A:WAVE.TMP",
      "%r / %r" % (cstr(0x50bd68), cstr(0x50bd5c)))
check("A8 扩展名分派常量：'.KOB' → A:MIDI.TMP",
      cstr(0x50bd7c) == ".KOB" and cstr(0x50bd70) == "A:MIDI.TMP",
      "%r / %r" % (cstr(0x50bd7c), cstr(0x50bd70)))
s3 = dstr(0x4993d1, 0x48)
check("A9 分派逻辑：strchr(name,'.') 后 0x4f43f0 比 .KOB 再比 .KOS",
      "0x499360" in s3 and s3.count("0x4f43f0") == 2, s3)

# 0x499360 = strchr
s4 = dstr(0x499360, 0x20)
check("A10 0x499360 = strchr(s, c)（逐字节 cmp，命中返回指针/否则 0）",
      "cmp" in s4 and "xor" in s4 and "ret" in s4, s4)

# ══════════════════════════════════════════════════════════════════
# B. 文件侧：全 39 个 KOS 验证
# ══════════════════════════════════════════════════════════════════
print("\n[B] 39 个 KOS 文件结构验证")

files = sorted(f for f in os.listdir(ORIG) if f.upper().endswith(".KOS"))
check("B0 原版目录 KOS 文件数 == 39（与音效指针表项数吻合）",
      len(files) == 39, "got %d" % len(files))


def xor16(buf, key16, length=None):
    """复刻 0x499380：16 位为单位 XOR，计数 ceil(len/2)。"""
    b = bytearray(buf)
    n = len(b) if length is None else length
    cnt = (n + 1) >> 1
    lo = key16 & 0xFF
    hi = (key16 >> 8) & 0xFF
    for i in range(cnt):
        p = i * 2
        if p < len(b):
            b[p] ^= lo
        if p + 1 < len(b) and p + 1 < n:
            b[p + 1] ^= hi
    return bytes(b)


def parse_kos(path):
    raw = open(path, "rb").read()
    key = raw[0]
    key16 = key | (key << 8)
    body = xor16(raw[1:], key16)          # ★ 密钥字节不参与 XOR
    return raw, key, key16, body


rows = []
bad = []
for f in files:
    raw, key, key16, d = parse_kos(os.path.join(ORIG, f))
    riff = d[0:4]
    rsz = struct.unpack("<I", d[4:8])[0]
    wave = d[8:12]
    fmt = d[12:16]
    fsz = struct.unpack("<I", d[16:20])[0]
    af, nch, sr, br, ba, bps = struct.unpack("<HHIIHH", d[20:36])
    dc = d[36:40]
    dsz = struct.unpack("<I", d[40:44])[0]
    payload = d[44:]
    pad = payload[dsz:]
    ok = (riff == b"RIFF" and wave == b"WAVE" and fmt == b"fmt "
          and fsz == 16 and dc == b"data"
          and rsz == len(d) - 8          # RIFF size = 解码后总长 - 8
          and dsz <= len(payload)
          and len(pad) == (dsz & 1)      # 奇长补 1 字节 pad
          and af == 1 and nch == 1 and sr == 22050
          and br == 22050 and ba == 1 and bps == 8
          and len(d) == len(raw) - 1)
    rows.append(dict(file=f, key=key, rawsize=len(raw), riffsize=rsz,
                     datasize=dsz, pad=len(pad), secs=round(dsz / 22050.0, 3),
                     ok=ok))
    if not ok:
        bad.append((f, riff, wave, fmt, dc, rsz, len(d) - 8, dsz, len(payload)))

check("B1 全部 39 个：解码后 = 标准 RIFF/WAVE/fmt(16)/data，且 RIFF size 自洽",
      not bad, "%d 处异常: %s" % (len(bad), bad[:3]))
check("B2 全部 39 个：PCM 参数恒为 af=1 ch=1 sr=22050 br=22050 align=1 bits=8",
      all(r["ok"] for r in rows))

keys = sorted(set(r["key"] for r in rows))
check("B3 第 0 字节（XOR 密钥）取值集合", keys == [0xAE], str([hex(k) for k in keys]))
check("B4 密钥字节自洽：raw[0] ^ key == 0（密钥不参与 XOR，故解码后首字节为 0）",
      all((open(os.path.join(ORIG, f), "rb").read(1)[0] ^ 0xAE) == 0 for f in files))

# 等价性：整文件 XOR 与「跳过密钥字节再 xor16」结果一致
same = 0
for f in files:
    raw = open(os.path.join(ORIG, f), "rb").read()
    naive = bytes(x ^ 0xAE for x in raw)          # 逐字节（含密钥字节）
    _, _, _, body = parse_kos(os.path.join(ORIG, f))
    if naive[1:] == body:
        same += 1
check("B5 逐字节 XOR（含密钥字节）与 xor16（跳过密钥字节）结果完全一致",
      same == len(files), "%d/%d" % (same, len(files)))

odd = [r["file"] for r in rows if r["datasize"] & 1]
check("B6 奇数 data 长度的文件恰有 1 字节 pad（RIFF 对齐规则）",
      sorted(odd) == ["CLICK.KOS", "NIGERU.KOS", "OOATARI.KOS"], str(odd))
# B7 用「统计指纹」而非逐文件起始值（39 个音效开头未必静音）：
# 8bit 无符号 PCM 的静音中心是 128，且波形相邻样本变化平缓。
_dec_all = b""
_raw_all = b""
for f in files:
    _raw, _, _, _d = parse_kos(os.path.join(ORIG, f))
    _dec_all += _d[44:]
    _raw_all += _raw[45:]
_dec_mean = sum(_dec_all) / float(len(_dec_all))


def _adjdiff(b):
    return sum(abs(b[i + 1] - b[i]) for i in range(len(b) - 1)) / float(len(b) - 1)


_d_dec = _adjdiff(_dec_all)
_d_raw = _adjdiff(_raw_all)
check("B7 解码后统计指纹 = 8bit 无符号 PCM：均值≈128（静音中心）",
      120.0 <= _dec_mean <= 136.0, "mean=%.2f" % _dec_mean)
check("B7b 解码后波形平滑度远优于未解码（%.2f vs %.2f，>3×  ⇒ 变换正确）"
      % (_d_dec, _d_raw), _d_raw > 3.0 * _d_dec, "dec=%.2f raw=%.2f" % (_d_dec, _d_raw))
check("B7c 解码后取值覆盖完整 0..255 动态范围（min=0 / max=255）",
      min(_dec_all) == 0 and max(_dec_all) == 255,
      "min=%d max=%d" % (min(_dec_all), max(_dec_all)))

# 复刻 EXE 的分块循环（块长 255），验证与一次性解码等价
chunk_eq = 0
for f in files:
    raw, key, key16, body = parse_kos(os.path.join(ORIG, f))
    data = bytearray(raw[1:])
    CH = 255
    out = bytearray()
    for off in range(0, len(data), CH):
        blk = bytes(data[off:off + CH])
        out += xor16(blk, key16)
    if bytes(out[:len(body)]) == body[:len(out)]:
        chunk_eq += 1
check("B8 复刻 EXE 分块循环（块长 255）逐字节等价于一次性解码",
      chunk_eq == len(files), "%d/%d" % (chunk_eq, len(files)))

# ══════════════════════════════════════════════════════════════════
# C. 与音效子系统对接（续195）
# ══════════════════════════════════════════════════════════════════
print("\n[C] 与音效子系统（@0x50ba40 指针表 / 续195）对接")

SFX_TBL = 0x50ba40
tbl = []
for i in range(40):
    p = struct.unpack("<I", rd(SFX_TBL + 4 * i, 4))[0]
    tbl.append(cstr(p, 24))
names39 = [t for t in tbl if t.upper().endswith(".KOS")]
check("C1 @0x50ba40 表中 .KOS 条目数 == 39", len(names39) == 39,
      "%d: %s" % (len(names39), names39[:5]))
check("C2 表中的 39 个 KOS 名 == 原版目录 39 个文件名（剥 'X:' 盘符前缀后）",
      sorted(n.split(":")[-1].upper() for n in names39) == sorted(files),
      "表=%s" % sorted(n.split(":")[-1].upper() for n in names39)[:5])

# ID → 文件
idmap = {}
for i, t in enumerate(tbl):
    if t.upper().endswith(".KOS"):
        base = t.split(":")[-1].upper()
        idmap[i] = base
check("C3 39 个 KOS 全部能映射到音效 ID 0..38", len(idmap) == 39,
      "%d" % len(idmap))

byfile = {r["file"]: r for r in rows}
miss = [n for n in idmap.values() if n not in byfile]
check("C4 每个 ID 的文件都能在原版目录找到", not miss, str(miss[:5]))

# ══════════════════════════════════════════════════════════════════
# D. 全量解码输出
# ══════════════════════════════════════════════════════════════════
print("\n[D] 全量解码 -> scripts/_decoded_kos/*.wav")
outdir = os.path.join(HERE, "_decoded_kos")
os.makedirs(outdir, exist_ok=True)
n_out = 0
for f in files:
    _, _, _, body = parse_kos(os.path.join(ORIG, f))
    open(os.path.join(outdir, f[:-4] + ".wav"), "wb").write(body)
    n_out += 1
check("D1 39 个 WAV 已导出到 scripts/_decoded_kos/", n_out == 39, "%d" % n_out)

manifest = []
for sid in sorted(idmap):
    fn = idmap[sid]
    r = byfile[fn]
    manifest.append(dict(id=sid, kos=fn, wav=fn[:-4] + ".wav",
                         key=hex(r["key"]), bytes=r["rawsize"],
                         samples=r["datasize"], seconds=r["secs"]))
import json
mp = os.path.join(HERE, "kos_sfx_manifest.json")
json.dump(dict(format=dict(
    layout="u8 key @0 (0xAE) ; rest = WAV, every byte XOR key",
    decoder_va="0x499380(xor16) / 0x4993a0(dispatch)",
    pcm=dict(format=1, channels=1, rate=22050, bits=8,
             note="byterate 22050, blockalign 1"),
    dispatch={".KOS": "A:WAVE.TMP", ".KOB": "A:MIDI.TMP", "*": "no decode"},
    chunk_bytes=255),
    sfx=manifest), open(mp, "w"), ensure_ascii=False, indent=1)
check("D2 机器可读清单 scripts/kos_sfx_manifest.json 已生成",
      os.path.exists(mp))

# ══════════════════════════════════════════════════════════════════
print("\n[E] 音效 ID → 文件 → 时长（前 12 / 共 %d）" % len(manifest))
for m in manifest[:12]:
    print("   ID %2d  %-16s %7d B  %6d samples  %6.3f s  key=%s"
          % (m["id"], m["kos"], m["bytes"], m["samples"], m["seconds"], m["key"]))
tot = sum(m["seconds"] for m in manifest)
print("   ...")
print("   合计 %.2f s 音频（%d 条）" % (tot, len(manifest)))

print("\n" + "=" * 68)
print("RESULT: %d PASS / %d FAIL" % (PASS, FAIL))
print("=" * 68)
sys.exit(1 if FAIL else 0)
