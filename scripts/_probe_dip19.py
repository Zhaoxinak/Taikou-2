# -*- coding: utf-8 -*-
"""
_probe_dip19.py — 工作完了结算【总 dump】
  A) 映射表 0x4b985c byte[45] + 跳表 0x4b981c dword[N] -> work -> handler
  B) 消息 0x920..0x936
  C) 0x4d9e50 (目标国属性) / 0x4b9c10
  D) 0x4b956e 成功率块（精读） + 0x4b97a8 共通尾
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

import json, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
MEM = open(MEM_PATH, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

MAP, NMAP, JT = 0x4B985C, 45, 0x4B981C


def dis(va, maxb=0x400, maxins=120):
    o = va - BASE
    out = []
    for ins in md.disasm(MEM[o:o + maxb], va):
        out.append(f"  {ins.address:#x}  {ins.mnemonic:<8} {ins.op_str}")
        if len(out) >= maxins or ins.mnemonic == "ret":
            break
    return "\n".join(out)


print("=" * 78)
print("### A) 结算跳表: 0x4b985c (byte[45]) + 0x4b981c (dword[])")
print("=" * 78)
mo = MAP - BASE
m = list(MEM[mo:mo + NMAP])
mx = max(m)
jt = []
for i in range(mx + 1):
    o = JT - BASE + i * 4
    jt.append(struct.unpack("<I", MEM[o:o + 4])[0])
print(f"  handler 数 = {mx + 1}")
for i in range(mx + 1):
    print(f"    h[{i:2}] {JT + i*4:#x} -> {jt[i]:#x}")
print()
print("  work -> handler:")
seen = {}
for i, v in enumerate(m):
    w = i + 2
    seen.setdefault(jt[v], []).append(w)
for h in sorted(seen):
    print(f"    {h:#x}  <- work {seen[h]}")

print()
print("=" * 78)
print("### B) 消息 0x920..0x937")
print("=" * 78)
d = json.load(open(_ROOT + '/scripts/msgx_all_texts.json', encoding="utf-8"))
T = {}
for k, v in d["texts"].items():
    try:
        T[int(k)] = v
    except Exception:
        pass
for gid in range(0x920, 0x938):
    print(f"  {gid:#6x} ({gid}): {T.get(gid, '<none>')}")

print()
print("=" * 78)
print("### C1) 0x4d9e50 —— 目标国属性（成功率公式里的 attr）")
print("=" * 78)
print(dis(0x4D9E50, 0x300, 90))
print()
print("### C2) 0x4b9c10")
print("=" * 78)
print(dis(0x4B9C10, 0x300, 90))

print()
print("=" * 78)
print("### D1) 0x4b956e 成功率块（精读）")
print("=" * 78)
print(dis(0x4B956E, 0x120, 45))

print()
print("### D2) 0x4b97a8 共通尾")
print("=" * 78)
print(dis(0x4B97A8, 0x200, 70))
