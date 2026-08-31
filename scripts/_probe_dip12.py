# -*- coding: utf-8 -*-
"""
_probe_dip12.py — 用「外交结果消息」反查结算代码
  A) 在 msgx 全文本里搜外交结算关键词
  B) 对命中的消息 id, 扫全映像的 `push imm32` (68 xx) 找引用点
"""
import json, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
MEM = open(MEM_PATH, "rb").read()
SZ = len(MEM)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

d = json.load(open("F:/Games/Taikou 2/scripts/msgx_all_texts.json", encoding="utf-8"))
texts = d["texts"]
# 统一成 {int: str}
T = {}
for k, v in texts.items():
    try:
        T[int(k)] = v
    except Exception:
        pass
print(f"  msgx 条目: {len(T)}")

KEYS = ["屈服", "従属", "从属", "同盟", "関係", "关系", "改善", "悪化", "恶化",
        "使者", "外交", "圧力", "压力", "交渉", "交涉", "手切", "断交", "和睦",
        "貢物", "贡物", "寝返", "調略", "调略", "説得", "说服"]

print()
print("=" * 78)
print("### A) 关键词命中消息")
print("=" * 78)
hits = {}
for gid, txt in sorted(T.items()):
    for k in KEYS:
        if k in txt:
            hits.setdefault(gid, (txt, []))
            hits[gid][1].append(k)
            break
for gid in sorted(hits):
    txt, ks = hits[gid]
    print(f"  {gid:#6x} ({gid:5d}) file{gid//2000+1}#{gid%2000:<4} [{','.join(ks)}] {txt}")

print()
print("=" * 78)
print("### B) 这些 id 在映像中的 `push imm32` 引用点")
print("=" * 78)


def find_push_imm(gid):
    pat = b"\x68" + struct.pack("<I", gid)
    r = []
    i = MEM.find(pat)
    while i != -1:
        r.append(BASE + i)
        i = MEM.find(pat, i + 1)
    return r


def func_start(va):
    o = va - BASE
    lim = max(0, o - 0x900)
    i = o
    while i > lim:
        b = MEM[i]
        if b == 0xC3:
            return BASE + i + 1
        if b == 0xC2 and i + 2 < SZ:
            return BASE + i + 3
        i -= 1
    return BASE + lim


found = {}
for gid in sorted(hits):
    ps = find_push_imm(gid)
    if ps:
        found[gid] = ps
        print(f"  {gid:#6x} {hits[gid][0][:40]:<42} -> {len(ps)} 处: "
              f"{[hex(x) for x in ps][:8]}")
print(f"\n  有引用的消息: {len(found)} / {len(hits)}")


def dis(va, maxins=200):
    o = va - BASE
    out = []
    for ins in md.disasm(MEM[o:o + maxins * 8], va):
        out.append(f"  {ins.address:#x}  {ins.mnemonic:<8} {ins.op_str}")
        if len(out) >= maxins or ins.mnemonic == "ret":
            break
    return "\n".join(out)


# 优先看 0x4b/0x4c 区域（评议/外交/月次结算）
print()
print("=" * 78)
print("### C) 0x4b0000..0x4d0000 内的引用点所属函数")
print("=" * 78)
seen = set()
for gid in sorted(found):
    for p in found[gid]:
        if not (0x4B0000 <= p < 0x4D0000):
            continue
        fs = func_start(p)
        if fs in seen:
            continue
        seen.add(fs)
        print(f"\n========== msg {gid:#x} @{p:#x}  func {fs:#x} ==========")
        print(dis(fs, 200))
