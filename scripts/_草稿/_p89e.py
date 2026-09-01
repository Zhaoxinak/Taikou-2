# -*- coding: utf-8 -*-
"""_p89e.py — 干净全镜像扫描 5 个战斗标志的读写点 + setter caller（P1 #89）"""
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

import pickle, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
IMG = open(_ROOT + '/scripts/_unpacked_mem.bin', "rb").read(); BASE = 0x400000
D = pickle.load(open("_insn_addrs.pkl", "rb"))
FSTART_VA = sorted(o + BASE for o in D[1])
md = Cs(CS_ARCH_X86, CS_MODE_32); md.skipdata = True

FLAGS = {
    "mode_m1": 0x511bf8, "mode_m2": 0x51352c, "parity": 0x513540,
    "battle_type": 0x513548, "handle_stat": 0x513534,
}
def enclosing(va):
    best = None
    for f in FSTART_VA:
        if f <= va: best = f
        else: break
    return best
def callers_of(target, win=0x1000):
    hits = []
    for va in range(BASE, BASE + len(IMG), win):
        for r in md.disasm(IMG[va-BASE:va-BASE+win], va):
            if r.mnemonic == "call":
                try: t=int(r.op_str,16)
                except: continue
                if t==target: hits.append(va)
    return hits

# 干净扫描：找所有引用各标志地址的 mov 指令
refs = {k: {"w": [], "r": []} for k in FLAGS}
for va in range(BASE, BASE + len(IMG), 0x800):
    for r in md.disasm(IMG[va-BASE:va-BASE+0x800], va):
        s = r.mnemonic + " " + r.op_str
        for k, ad in FLAGS.items():
            tok = "[0x%x]" % ad
            if tok in r.op_str:
                if r.op_str.strip().endswith(tok):   # 目标是 [addr] => 写
                    refs[k]["w"].append((r.address, s))
                else:                                  # 源是 [addr] => 读
                    refs[k]["r"].append((r.address, s))

for k in FLAGS:
    print("==== %s @0x%x ====" % (k, FLAGS[k]))
    print("  WRITE sites (%d):" % len(refs[k]["w"]))
    for va, s in refs[k]["w"][:20]:
        fn = enclosing(va)
        print("    0x%x (%s func=0x%x): %s" % (va, s.split('[')[0].strip(), fn, s))
    print("  READ sites (%d):" % len(refs[k]["r"]))
    for va, s in refs[k]["r"][:8]:
        print("    0x%x: %s" % (va, s))

# 对每个 WRITE 站点所属函数，找 caller
print("\n##### setter caller 汇总 #####")
seen=set()
for k in FLAGS:
    for va, s in refs[k]["w"]:
        fn = enclosing(va)
        if fn in seen: continue
        seen.add(fn)
        cs = callers_of(fn)
        print("  %s setter func=0x%x -> callers=%s" % (k, fn, [hex(c) for c in cs]))
