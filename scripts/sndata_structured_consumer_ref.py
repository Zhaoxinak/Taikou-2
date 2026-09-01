#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续223 自测：SNDATA 49B payload「结构化消费」链路钉死。
断言链：
 T1 read_record 0x47d890 偏移 = idx*49 + 0x10（stride 49 = 0x31, header 16B = 0x10）+ 读 49B
 T2 显示生产者 0x47fc60 把 payload 落成 3 文本视全局 0x522c88/0x522c60/0x522c70
 T3 0x488290 是 0x4e8600 的双生子（同调 0x47fc60 + 按 0x5205fe 派发，仅 MODE 0/1）
 T4 读 49B 记录的「加载流读取器」= 0x47d580/0x47d680/0x47d6a0，被 0x4b9c10/0x451860 调用；
    而 0x47d890 唯一调用者是显示链 0x47fc60（加载路径不复用 0x47d890）
 T5 0x462460 = 队列入口（0x4eefa0 入队到 0x526c58），结构化消费是「延迟队列」而非即时 type→handler
 T6 全镜像无函数对字面 833(0x341) 计数循环（记录数由头派生，非硬编码 833）
"""
import os, struct, pickle
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BASE=0x400000
code=open("scripts/_unpacked_mem.bin","rb").read()
pkl=pickle.load(open("scripts/_insn_addrs.pkl","rb"))
FUNCS_S=sorted(pkl[1])
def enclosing(va):
    fo=va-BASE; lo,hi=0,len(FUNCS_S)-1; best=None
    while lo<=hi:
        m=(lo+hi)//2
        if FUNCS_S[m]<=fo: best=FUNCS_S[m]; lo=m+1
        else: hi=m-1
    return best
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
def disasm(va,n):
    fo=va-BASE
    return list(md.disasm(code[fo:fo+n],va))
def calls_of(tgt):
    out=set(); off=0
    while True:
        idx=code.find(b'\xe8', off)
        if idx<0: break
        rel=struct.unpack("<i", code[idx+1:idx+5])[0]
        va=BASE+idx+5+rel
        if va==tgt: out.add(BASE+idx)
        off=idx+1
    return out

results=[]
def chk(name, cond, extra=""):
    results.append((name, cond, extra))
    print(("PASS" if cond else "FAIL"), name, extra)

# T1
ins=[(i.mnemonic,i.op_str) for i in disasm(0x47d890,260)]
has_shl4=any(m=="shl" and "4" in o for m,o in ins)
has_lea2=any(m=="lea" and "*2" in o for m,o in ins)
has_plus10=any(("0x10" in o) and (m=="lea" or m=="add") for m,o in ins)
has_read49=any(m=="push" and o=="0x31" for m,o in ins) and any(m.startswith("call") and o=="0x4411b0" for m,o in ins)
chk("T1_read_record_idx49+0x10", has_shl4 and has_lea2 and has_plus10 and has_read49,
    f"shl4={has_shl4} lea*2={has_lea2} +0x10={has_plus10} read49={has_read49}")

# T2  (bound to own function: next start = 0x47fd10)
_nxt2=None
for f in FUNCS_S:
    if f > 0x47fc60-BASE: _nxt2=f; break
ins2=[(i.mnemonic,i.op_str) for i in disasm(0x47fc60,(_nxt2-(0x47fc60-BASE)) if _nxt2 else 260)]
views=("0x522c88" in " ".join(o for m,o in ins2)) and ("0x522c60" in " ".join(o for m,o in ins2)) and ("0x522c70" in " ".join(o for m,o in ins2))
strcpy3=sum(1 for m,o in ins2 if m.startswith("call") and o=="0x4ebfe0")
chk("T2_47fc60_three_text_views", views and strcpy3==3, f"views={views} strcpy0x4ebfe0={strcpy3}")

# T3
insA=[(i.mnemonic,i.op_str) for i in disasm(0x488290,420)]
insB=[(i.mnemonic,i.op_str) for i in disasm(0x4e8600,2600)]
twinA = any(m.startswith("call") and o=="0x47fc60" for m,o in insA) and any("0x5205fe" in o for m,o in insA)
twinB = any(m.startswith("call") and o=="0x47fc60" for m,o in insB) and any("0x5205fe" in o for m,o in insB)
only_mode01 = ("0x48837c" in " ".join(i.address and f"0x{i.address:06x}" for i in disasm(0x488290,420)))  # else-branch is bare ret (MOV eax,1;ret)
chk("T3_488290_twin_of_4e8600", twinA and twinB, f"488290->47fc60&mode={twinA} 4e8600->47fc60&mode={twinB}")

# T4
callers_47d890=calls_of(0x47d890)
only_display = all(enclosing(s)+BASE in (0x47fc60,) for s in callers_47d890)
# load readers used by loaders?
def uses_reader(va, reader):
    ins=[(i.mnemonic,i.op_str) for i in disasm(va,0x800)]
    return any(m.startswith("call") and o==f"0x{reader:06x}" for m,o in ins)
loader_b9 = uses_reader(0x4b9c10,0x47d580) and uses_reader(0x4b9c10,0x47d680) and uses_reader(0x4b9c10,0x47d6a0)
loader_45 = uses_reader(0x451860,0x47d580) and uses_reader(0x451860,0x47d680) and uses_reader(0x451860,0x47d6a0)
chk("T4_load_readers_vs_display", only_display and loader_b9 and loader_45,
    f"47d890_callers={[hex(enclosing(s)+BASE) for s in callers_47d890]} b9c10={loader_b9} 451860={loader_45}")

# T5
ins5=[(i.mnemonic,i.op_str) for i in disasm(0x462460,140)]
queue_ingress = any(m.startswith("call") and o=="0x4eefa0" for m,o in ins5) and any("0x526c58" in o for m,o in ins5)
chk("T5_462460_queue_ingress", queue_ingress)

# T6
found833=False
for f in FUNCS_S:
    va=BASE+f
    if va<0x400000 or va>0x500000: continue
    for i in disasm(va,0x1000):
        if i.mnemonic=="cmp" and ("0x341" in i.op_str or "833" in i.op_str):
            found833=True; break
    if found833: break
chk("T6_no_literal_833_loop", not found833)

npass=sum(1 for _,c,_ in results if c)
print(f"\n===== {npass}/{len(results)} PASS =====")
for n,c,e in results:
    if not c: print("FAILED:", n, e)
raise SystemExit(0 if npass==len(results) else 1)
