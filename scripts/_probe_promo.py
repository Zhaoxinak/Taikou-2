# -*- coding: utf-8 -*-
"""侦察晋升 ladder 0x50d850：导出该地址起的字符串指针表 / 邻近字节 / 引用点。"""
import struct, os, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
mem = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
N = len(mem)

def cstr(va, maxn=64):
    o = va - BASE
    if o < 0 or o >= N:
        return None
    e = mem.find(b"\x00", o, o + maxn)
    if e < 0:
        e = o + maxn
    return mem[o:e].decode("gbk", "replace")

def w(va):
    return struct.unpack_from("<H", mem, va - BASE)[0]

def d(va):
    return struct.unpack_from("<I", mem, va - BASE)[0]

out = []

# 1) 导出 0x50d850 起 16 个 dword（看是否指针表）
out.append("=== 0x50d850 起 20 个 dword ===")
for i in range(20):
    va = 0x50d850 + 4 * i
    v = d(va)
    in_str = cstr(v, 32) if (BASE <= v < BASE + N) else None
    out.append(f"  [{i:2d}] {va:#010x} = {v:#010x}  -> {in_str!r}" if in_str else f"  [{i:2d}] {va:#010x} = {v:#010x}")

# 2) 邻近区 0x50d830..0x50da80 原始字节（GBK 解读）
out.append("\n=== 0x50d830..0x50da80 字符串区 ===")
raw = mem[0x50d830 - BASE:0x50da80 - BASE]
out.append(repr(raw.decode("gbk", "replace")))

# 3) 引用点：全映像找 const 0x50d850
out.append("\n=== xref: 0x50d850 立即数引用 ===")
pat = struct.pack("<I", 0x50d850)
i = 0
hits = []
while True:
    i = mem.find(pat, i)
    if i < 0:
        break
    hits.append(BASE + i)
    i += 1
out.append(f"  {len(hits)} 处: " + " ".join(hex(h) for h in hits[:20]))

# 4) 作为字符串指针表：若前几项都指向可读串，导出全部
out.append("\n=== 若是指针表：前 12 项指向的文本 ===")
ok = 0
names = []
for i in range(16):
    v = d(0x50d850 + 4 * i)
    t = cstr(v, 40)
    if t is not None and t.strip():
        ok += 1
        names.append(t)
    else:
        break
out.append(f"  连续有效串 {ok} 项: {names}")

txt = "\n".join(out)
open(os.path.join(HERE, "_probe_promo.txt"), "w", encoding="utf-8").write(txt)
print(txt)
