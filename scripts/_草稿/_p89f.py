# -*- coding: utf-8 -*-
"""_p89f.py — 修正版：正确区分写点(目标含[addr])，找 setter 函数 + caller + 采样 battle_type 值"""
import pickle, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
IMG = open("_unpacked_mem.bin", "rb").read(); BASE = 0x400000
D = pickle.load(open("_insn_addrs.pkl", "rb"))
FSTART_VA = sorted(o + BASE for o in D[1])
md = Cs(CS_ARCH_X86, CS_MODE_32); md.skipdata = True

FLAGS = {"mode_m1":0x511bf8,"mode_m2":0x51352c,"parity":0x513540,
         "battle_type":0x513548,"handle_stat":0x513534}
def enclosing(va):
    best=None
    for f in FSTART_VA:
        if f<=va: best=f
        else: break
    return best
def callers_of(t,win=0x1000):
    out=[]
    for va in range(BASE,BASE+len(IMG),win):
        for r in md.disasm(IMG[va-BASE:va-BASE+win],va):
            if r.mnemonic=="call":
                try: tt=int(r.op_str,16)
                except: continue
                if tt==t: out.append(va)
    return out

# 正确扫描写点
writes={k:[] for k in FLAGS}
for va in range(BASE,BASE+len(IMG),0x800):
    for r in md.disasm(IMG[va-BASE:va-BASE+0x800],va):
        s=r.op_str
        for k,ad in FLAGS.items():
            tok="[0x%x]"%ad
            if tok in s:
                dst=s.split(",")[0]   # 目标操作数
                if tok in dst:        # 目标是 [addr] => 写
                    writes[k].append(r.address)

print("==== 各标志真实写点 + setter 函数 ====")
setters={}
for k in FLAGS:
    addrs=writes[k]
    fns=set(enclosing(a) for a in addrs)
    setters[k]=sorted(fns)
    print("%s: write@%s  setter_funcs=%s" % (k, [hex(a) for a in addrs], [hex(f) for f in setters[k]]))

print("\n==== setter caller ====")
for k in FLAGS:
    for f in setters[k]:
        cs=callers_of(f)
        print("%s setter 0x%x -> %d callers (e.g. %s)" % (k,f,len(cs),[hex(c) for c in cs[:6]]))

# 采样 battle_type setter 0x43ca10 调用点前 6 条，抓设定值
print("\n==== battle_type setter 0x43ca10 调用点采样（前8指令）====")
bt_set = setters["battle_type"][0]
cs = callers_of(bt_set)
import collections
for c in cs[:14]:
    print("-- caller 0x%x --" % c)
    code=IMG[c-0x30-BASE:c+4-BASE]
    for r in md.disasm(code, c-0x30):
        mark = " <<<CALL" if r.address==c else ""
        print("   0x%x:\t%s\t%s%s" % (r.address, r.mnemonic, r.op_str, mark))
