# -*- coding: utf-8 -*-
"""① 反汇编 0x4c7c30 (技能 getter 候选)  ② 按新布局(10技能×2bit)抽 BSDATA 并用史实人物验证。"""
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

import json
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = _ROOT + '/scripts/_unpacked_mem.bin'
BSD = _ROOT + '/Taikou2 Original/BSDATA1.TR2'
BASE = 0x400000
mem = open(MEM_PATH, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)

print("=" * 78)
print("A. 0x4c7c30 (引用 +0xf/+0x10/+0x11 最均衡)")
print("=" * 78)
o = 0x4C7C30 - BASE
n = 0
for ins in md.disasm(mem[o:o + 1200], 0x4C7C30):
    print(f"  {ins.address:08x}  {ins.mnemonic:<8} {ins.op_str}")
    n += 1
    if ins.mnemonic == "ret" or n > 75:
        break

print("\n" + "=" * 78)
print("B. 新布局抽取: 技能[i] = (byte[27 + i//4] >> (2*(i%4))) & 3")
print("=" * 78)
b = open(BSD, "rb").read()
SKILLS = ["口才", "马术", "算术", "剑术", "忍术", "兵法", "洋枪", "筑城", "礼法", "茶道"]
REC = 59
N = 700

name_of = {}
for i in range(N):
    off = REC * i
    fam = b[off:off + 7].split(b"\x00")[0].decode("gbk", "replace")
    giv = b[off + 7:off + 13].split(b"\x00")[0].decode("gbk", "replace")
    name_of[i] = fam + giv


def skill(rec, i):
    byte = b[REC * rec + 27 + i // 4]
    return (byte >> (2 * (i % 4))) & 3


# 分布检查
from collections import Counter
print("  各技能取值分布 (0..3):")
for i, s in enumerate(SKILLS):
    c = Counter(skill(r, i) for r in range(N))
    print(f"    [{i}] {s}: " + " ".join(f"{v}:{c.get(v,0)}" for v in range(4)))

# @29 高 nibble 应恒 0 (只存技能8/9于 bit0-3)
hi29 = Counter((b[REC * r + 29] >> 4) & 0xF for r in range(N))
print(f"\n  @29 高 nibble 分布: {dict(hi29)}   (若全 0 ⇒ 只用了低 4 位=技能8/9)")

print("\n  史实人物技能抽查 (期望高亮项):")
checks = [
    ("柳生宗矩", 3, "剑术"), ("上泉信纲", 3, "剑术"), ("塚原卜传", 3, "剑术"),
    ("武田信玄", 5, "兵法"), ("上杉谦信", 5, "兵法"), ("毛利元就", 5, "兵法"),
    ("千利休", 9, "茶道"), ("今井宗久", 9, "茶道"), ("津田宗及", 9, "茶道"),
    ("石川五右卫门", 4, "忍术"), ("服部半藏", 4, "忍术"), ("百地三太夫", 4, "忍术"),
    ("黒田官兵卫", 0, "口才"), ("竹中半兵卫", 5, "兵法"),
    ("藤堂高虎", 7, "筑城"), ("真田幸村", 5, "兵法"),
]
for nm, si, sn in checks:
    hit = [r for r in range(N) if name_of[r] == nm]
    if not hit:
        print(f"    {nm:<8} 未找到")
        continue
    r = hit[0]
    vals = {SKILLS[i]: skill(r, i) for i in range(10)}
    top = sorted(vals.items(), key=lambda x: -x[1])
    mark = "★" if vals[sn] == 3 else ("○" if vals[sn] >= 2 else "·")
    print(f"    {mark} {nm:<8} {sn}={vals[sn]}  全技能 {vals}")
