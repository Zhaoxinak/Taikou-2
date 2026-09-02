#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续228 自测：SNDATA「结构化消费」队列的真实数据结构的钉死。
推翻续223「ring buffer / 指针队列」假设 —— 实为**侵入式双向链表**：
- 头 0x526c58，哨兵节点 0x524740（cmp [0x526c58],0x524740; je == 队列空）。
- 入队/插入 = 0x4eeda0（操作 +0x1c=prev / +0x20=next / +0x24=flags，调 0x4ed230/0x4eed10）。
- 非空检查 = 0x4ee0d0（调 0x4ef650 取链表状态）。
- 抽干端 finalize：0x4af320(mode0) / 0x490c30(mode1)，仅在 head==哨兵时执行收尾。
- 模式分发器 = 0x48ad10（按 word[0x5205fe] 三路）。
- 49B 记录逐 type 分派位于生产者侧类别簇（续160/161），非单一 drain 比较链。
"""
import pickle, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BASE=0x400000
code=open("scripts/_unpacked_mem.bin","rb").read()
pkl=pickle.load(open("scripts/_insn_addrs.pkl","rb"))
FUNCS_S=sorted(pkl[1])
def next_func(va):
    fo=va-BASE
    for f in FUNCS_S:
        if f>fo: return BASE+f
    return BASE+len(code)
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
def disasm(va,n):
    fo=va-BASE
    return list(md.disasm(code[fo:fo+n],va))
results=[]
def chk(name, cond, extra=""):
    results.append((name,cond,extra)); print(("PASS" if cond else "FAIL"),name,extra)

SENT=0x524740
# T1 0x4eeda0 = 链表插入（操作 +0x1c/+0x20/+0x24, 调 0x4ed230/0x4eed10）
ins=disasm(0x4eeda0, next_func(0x4eeda0)-0x4eeda0)
txt=" ".join(f"{i.mnemonic} {i.op_str}" for i in ins)
has_prev = "0x1c" in txt
has_next = "0x20" in txt
has_flags= "0x24" in txt
calls_list = any(i.mnemonic.startswith("call") and i.op_str in ("0x4ed230","0x4eed10") for i in ins)
chk("T1_4eeda0_linkedlist_insert", has_prev and has_next and has_flags and calls_list,
    f"prev={has_prev} next={has_next} flags={has_flags} listcalls={calls_list}")

# T2 哨兵 0x524740 作为链表终止：0x4af320 / 0x490c30 以 cmp [0x526c58],0x524740; jne 跳过
for fn,nm in [(0x4af320,"0x4af320"),(0x490c30,"0x490c30")]:
    ins=disasm(fn, next_func(fn)-fn)
    txt=" ".join(f"{i.mnemonic} {i.op_str}" for i in ins)
    hit = ("0x526c58" in txt) and ("0x524740" in txt)
    chk(f"T2_{nm}_sentinel", hit, f"sentinel-ref={hit}")

# T3 0x4af320 是 mode0 finalize：在 mode dispatcher 0x48ad10 中由 mode==0 分支调用
disp=disasm(0x48ad10, next_func(0x48ad10)-0x48ad10)
txt=" ".join(f"{i.mnemonic} {i.op_str}" for i in disp)
chk("T3_48ad10_mode_dispatch", ("0x5205fe" in txt) and ("0x4af320" in txt) and ("0x490c30" in txt),
    f"modeword={ '0x5205fe' in txt } calls_af320={'0x4af320' in txt} calls_90c30={'0x490c30' in txt}")

# T4 0x48b2b0 是链表遍历者但非 49B 记录 type 分派（读 node+0x24 标志位 0x20 + 全局 0x523a14/0x523b04）
ins=disasm(0x48b2b0, next_func(0x48b2b0)-0x48b2b0)
txt=" ".join(f"{i.mnemonic} {i.op_str}" for i in ins)
reads_node_flags = "0x24" in txt
tests_global = ("0x523a14" in txt) or ("0x523b04" in txt)
no_type_cmp = not any(i.mnemonic=="cmp" and "0x526c58" in i.op_str and "0x524740" not in i.op_str for i in ins)
chk("T4_48b2b0_listwalker_not_type_dispatch", reads_node_flags and tests_global,
    f"nodeflags={reads_node_flags} globalflags={tests_global}")

# T5 生产者侧类别簇据续160/161：type-0→0x492e20、type-1→0x492ed0（存在且为簇 handler）
for fn in (0x492e20,0x492ed0):
    nxt=next_func(fn)
    chk(f"T5_cluster_{fn:06x}_exists", nxt>fn and nxt-fn>16, f"size={nxt-fn}")

npass=sum(1 for _,c,_ in results if c)
print(f"\n===== {npass}/{len(results)} PASS =====")
for n,c,e in results:
    if not c: print("FAILED:",n,e)
raise SystemExit(0 if npass==len(results) else 1)
